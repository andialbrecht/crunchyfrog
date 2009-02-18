# -*- coding: utf-8 -*-

# crunchyfrog - a database schema browser and query tool
# Copyright (C) 2008 Andi Albrecht <albrecht.andi@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Main application window"""

import logging
import os
import webbrowser

import gobject
import gtk

try:
    import gnomevfs
    HAVE_GNOMEVFS = True
except ImportError:
    HAVE_GNOMEVFS = False

from cf import USER_CONFIG_DIR
from cf import release
from cf.backends import TRANSACTION_IDLE, TRANSACTION_COMMIT_ENABLED
from cf.backends import TRANSACTION_ROLLBACK_ENABLED
from cf.ui import pane
from cf.ui import utils
from cf.ui import widgets
from cf.ui.browser import Browser
from cf.ui.confirmsave import ConfirmSaveDialog
from cf.ui.datasources import DatasourceManager
from cf.ui.editor import Editor
from cf.ui.statusbar import CrunchyStatusbar


class MainWindow(gtk.Window):
    """Application main window.

    Instance attributes:
      menubar: Menu bar.

    :Signals:
    active-editor-changed
      ``def callback(instance, editor)``
      Emitted when the active editor has changed. editor is either an
      editor instance or None.
    """

    __gsignals__ = {
        'active-editor-changed': (gobject.SIGNAL_RUN_LAST,
                                  gobject.TYPE_NONE,
                                  (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, app, create_editor=True):
        gtk.Window.__init__(self)
        self.app = app
        self._editor = None
        self._editor_conn_tag = None  # Signal ID
        self._tracked_conn = None  # Tracked connection
        self._editors = []
        self.clipboard = gtk.clipboard_get()
        self.ui = gtk.UIManager()
        # See: http://www.daa.com.au/pipermail/pygtk/2006-May/012267.html
        self.ui.connect('connect-proxy', self.on_ui_connect_proxy)
        self.ui.connect('disconnect-proxy', self.on_ui_disconnect_proxy)
        self._init_actions()
        self.ui.add_ui_from_string(UI)
        self.ui.ensure_update()
        self.set_title("CrunchyFrog %s" % release.version)
        self.set_icon_list(*utils.get_logo_icon_list())
        self._init_elements()
        self.connect('window-state-event', self.on_window_state_event)
        self.connect('delete-event', self.on_quit)
        # XXX disabled: it results in unexpected behavior...
        if create_editor and 1 == 2:
            self.editor_create()
        self.state_restore()

    def _init_actions(self):
        group = gtk.ActionGroup('instance')
        group.set_data('cf::label', _(u'Application'))
        entries = (
            # File
            ('file-menu-action', None, _(u'_File')),
            ('instance-quit', gtk.STOCK_QUIT,
             None, '<control>Q', _(u'Quit the program'),
             self.on_quit),
            ('file-new-menu-action', None, _(u'_New')),
            ('instance-new-editor', gtk.STOCK_NEW,
             _(u'_Query'), '<control>N', _(u'New SQL editor'),
               self.on_editor_new),
            ('instance-new-mainwin', None,
             _(u'_Window'), '<shift><control>N',
             _('New application window.'),
             self.on_instance_new),
            ('file-open', gtk.STOCK_OPEN,
             None, '<control>O', _(u'Open a file'),
             self.on_open_file),
            # Edit
            ('edit-menu-action', None, _(u'_Edit')),
            ('instance-plugins', None,
             _(u'_Plugins'), None, _(u'Configure plugins'),
             lambda action: self.app.preferences_show(self, 'plugins')),
            ('instance-datasourcemanager', None, _(u'_Data Sources'),
             None, _(u'Add, edit and delete data sources'),
             self.on_datasource_manager),
            ('instance-preferences', gtk.STOCK_PREFERENCES,
             None, None, _(u'Configure the application'),
             lambda action: self.app.preferences_show(self)),
            # Query
            ('query-menu-action', None, _(u'_Query')),
            # View
            ('view-menu-action', None, _(u'_View')),
            # Help
            ('help-menu-action', None, _(u'_Help')),
            ('help-help', gtk.STOCK_HELP,
             None, 'F1', _(u'Open the CrunchyFrog manual'),
             lambda *a: self.app.show_help()),
            ('help-translate', None,
             _(u'Help translate...'), None,
             _(u'Help to translate this application'),
             lambda a:
             webbrowser.open('https://translations.launchpad.net/crunchyfrog'),
             ),
            ('help-bugs', None,
             _(u'Report a problem'), None,
             _((u'Help to improve this application by reporting a bug '
                u'or a feature request.')),
             lambda a:
             webbrowser.open(('http://code.google.com/p/crunchyfrog/'
                              'issues/entry'))),
            ('help-about', gtk.STOCK_ABOUT,
             None, None, _(u'About this application'),
             self.on_about),
        )
        group.add_actions(entries)
        toggle_entries = (
            ('instance-toggle-toolbar', None,
             _(u'_Toolbar'), None,
             _(u'Show or hide the toolbar in the current window'),
             self.on_toggle_toolbar),
            ('instance-toggle-statusbar', None,
             _(u'_Statusbar'), None,
             _(u'Show or hide the statusbar in the current window'),
             self.on_toggle_statusbar),
        )
        group.add_toggle_actions(toggle_entries)
        # Editor switcher
        entries = []
        for i in range(1, 11):
            if i == 10:
                i = 0
            entry = ('activate-editor%d' % i, None, '', '<Alt>%d' % i, None,
                     i-1)
            entries.append(entry)
        group.add_radio_actions(entries, 0, self.on_editor_set_focus)
        self.ui.insert_action_group(group, -1)
        group = gtk.ActionGroup('editor')
        group.set_data('cf::label', _(u'Editor'))
        entries = (
            ('editor-close', gtk.STOCK_CLOSE,
             None, '<control>W', _(u'Close the current editor'),
             self.on_editor_close),
            ('editor-close-all', None,
             _(u'Close _all'), '<control><shift>W', _(u'Close all editors'),
             lambda action: self.close_all_editors()),
            # Query
            ('query-connection-menu-action', None, _(u'_Connection')),
            ('query-connection-disconnect', gtk.STOCK_DISCONNECT,
             None, '<shift>F8',
             _(u'Disconnect current editor'),
             self.on_editor_disconnect),
            ('query-show-connections', None,
             _(u'Show connections'), '<shift>F5',
             _(u'Open or close connections in a dialog'),
             lambda *a: self.app.manage_connections(self)),
            ('query-frmt-menu', None, _(u'_Format')),
            ('query-frmt-comment', None,
             _(u'_Comment / Uncomment'), '<shift><control>c',
             _(u'Comment / uncomment selected lines'),
             self.on_frmt_comment),
            ('file-save', gtk.STOCK_SAVE,
             None, '<control>S', _(u'Save the current file'),
             self.on_file_save),
            ('file-save-as', gtk.STOCK_SAVE_AS,
             None, '<shift><control>S',
             _(u'Save the current file with a different name'),
             self.on_file_save_as),
            ('editor-print', gtk.STOCK_PRINT,
             None, '<control>P', _(u'Print the current page'),
             self.on_editor_print),
            ('editor-printpreview', gtk.STOCK_PRINT_PREVIEW,
             None, '<shift><control>P', _(u'Print preview'),
             self.on_editor_print_preview),
        )
        group.add_actions(entries)
        group.set_sensitive(False)
        self.ui.insert_action_group(group, 0)
        # Clipboard
        group = gtk.ActionGroup('clipboard')
        entries = (
            ('clipboard-cut', gtk.STOCK_CUT,
             None, '<control>X', _(u'Cut the selection'),
             self.on_clipboard_cut),
            ('clipboard-copy', gtk.STOCK_COPY,
             None, '<control>C', _(u'Copy the selection'),
             self.on_clipboard_copy),
            ('clipboard-paste', gtk.STOCK_PASTE,
             None, '<control>V', _(u'Paste the clipboard'),
             self.on_clipboard_paste),
            )
        group.add_actions(entries)
        self.ui.insert_action_group(group, 0)
        group = gtk.ActionGroup('query')
        group.set_data('cf::label', _(u'Queries'))
        entries = (
            ('query-execute', gtk.STOCK_EXECUTE,
             None, 'F5', _(u'Execute statements in SQL editor'),
             self.on_query_execute),
            ('query-begin', gtk.STOCK_INDENT,
             _(u'Transaction'), 'F6',
             _(u'Begin transaction on current connection'),
             self.on_begin_transaction),
            ('query-commit', gtk.STOCK_APPLY,
             _(u'Commit'), 'F7',
             _(u'Commit current transaction'),
             self.on_commit),
            ('query-rollback', gtk.STOCK_UNDO,
             _(u'Rollback'), 'F8',
             _(u'Rollback current transaction'),
             self.on_rollback),
        )
        group.add_actions(entries)
        group.set_sensitive(False)
        self.ui.insert_action_group(group, -1)
        self.add_accel_group(self.ui.get_accel_group())

    def _init_elements(self):
        """Initialize main window elements."""
        self._init_statusbar()
        self._init_panes()
        vbox = gtk.VBox()
        self.add(vbox)
        vbox.pack_start(self._init_menubar(), False, False)
        vbox.pack_start(self._init_toolbar(), False, False)
        hpaned = gtk.HPaned()
        vbox.pack_start(hpaned, True, True)
        hpaned.show()
        vpaned = gtk.VPaned()
        hpaned.add2(vpaned)
        vpaned.show()
        hpaned.add1(self.side_pane)
        vpaned.add2(self.bottom_pane)
        self.queries = pane.CenterPane(self)
        vpaned.add1(self.queries)
        self.queries.show()
        # Connect to realize to set paned position when window is ready.
        self.connect('realize', self.on_set_paned_position, vpaned)
        self.connect('realize', self.on_set_paned_position, hpaned)
        vbox.pack_start(self.statusbar, False, False)
        vbox.show()
        self.browser = Browser(self.app, self)
        self.side_pane.add_item(self.browser)
        self.side_pane.set_active_item('navigator')
        menu = self.ui.get_widget('/MenuBar/Query/Connection')
        menu.connect('activate', self.on_connection_menu_activate)
        menu = self.ui.get_widget('/MenuBar/Query')
        menu.connect('activate', self.on_query_menu_activate)
        self._init_file_open()

    def _init_file_open(self):
        """Initialize file open menu item and toolbar button."""
        ph = self.ui.get_widget("/ToolBar/OpenFile")
        btn = gtk.MenuToolButton(gtk.STOCK_OPEN)
        btn.show()
        btn.connect('clicked', self.on_open_file)
        btn.set_menu(self._get_recent_menu())
        idx = self.toolbar.get_item_index(ph)
        self.toolbar.insert(btn, idx)
        ph = self.ui.get_widget('/MenuBar/File/RecentFiles')
        menu = self._get_recent_menu()
        menuitem = gtk.MenuItem(_(u'_Recent Files'))
        menuitem.show()
        menuitem.set_submenu(menu)
        file_menu = self.ui.get_widget('/MenuBar/File').get_submenu()
        for idx, child in enumerate(file_menu.get_children()):
            if child == ph:
                file_menu.insert(menuitem, idx)
                return

    def _init_menubar(self):
        """Create and return the applications menubar."""
        self.menubar = self.ui.get_widget('/MenuBar')
        self.menubar.show_all()
        return self.menubar

    def _init_panes(self):
        """Init side and bottom pane."""
        self.side_pane = pane.SidePane(self)
        self.bottom_pane = pane.BottomPane(self)

    def _init_statusbar(self):
        """Create and return the statusbar."""
        self.statusbar = CrunchyStatusbar(self.app, self)
        self.statusbar.show()
        return self.statusbar

    def _init_toolbar(self):
        """Create and return the toolbar."""
        self.toolbar = self.ui.get_widget("/ToolBar")
        self.toolbar.show_all()
        ph = self.ui.get_widget("/ToolBar/EditorConnection")
        self.tb_conn_chooser = widgets.ConnectionButton(self)
        idx = self.toolbar.get_item_index(ph)
        self.toolbar.insert(self.tb_conn_chooser, idx)
        self.tb_conn_chooser.show_all()
        separator = gtk.SeparatorToolItem()
        self.toolbar.insert(separator, idx+1)
        separator.show()
        return self.toolbar

    def _get_action(self, action_name):
        """Return a action regardless of groups."""
        for group in self.ui.get_action_groups():
            action = group.get_action(action_name)
            if action is not None:
                return action
        return None

    def _get_clipboard(self):
        return self.clipboard

    def _get_recent_menu(self, limit=None, recent_menu=None):
        """Return a recent file menu."""
        if recent_menu is None:
            recent_menu = gtk.RecentChooserMenu(self.app.recent_manager)
        filter_ = gtk.RecentFilter()
        filter_.add_mime_type("text/x-sql")
        recent_menu.add_filter(filter_)
        recent_menu.set_filter(filter_)
        recent_menu.set_show_not_found(False)
        recent_menu.set_sort_type(gtk.RECENT_SORT_MRU)
        recent_menu.connect("item-activated", self.on_recent_item_activated)
        if limit is not None:
            recent_menu.set_limit(limit)
        return recent_menu

    # ---
    # Callbacks
    # ---
    def on_about(self, *args):
        def open_url(dialog, url):
            gtk.show_uri(dialog.get_screen(), url,
                         gtk.gdk.x11_get_server_time(dialog.window))
        gtk.about_dialog_set_url_hook(open_url)
        dlg = gtk.AboutDialog()
        dlg.set_name(release.name)
        dlg.set_version(release.version)
        dlg.set_copyright(release.copyright)
        dlg.set_license(release.license)
        dlg.set_website(release.url)
        dlg.set_website_label(release.url)
        dlg.set_logo(utils.get_logo_icon(96))
        dlg.set_program_name(release.appname)
        dlg.set_translator_credits(release.translators)
        dlg.run()
        dlg.destroy()


    def on_begin_transaction(self, *args):
        if not self._editor:
            return
        gobject.idle_add(self._editor.begin_transaction)

    def on_clipboard_copy(self, *args):
        if not self._editor:
            return
        buffer_ = self._editor.textview.get_buffer()
        buffer_.copy_clipboard(self._get_clipboard())

    def on_clipboard_cut(self, *args):
        if not self._editor:
            return
        buffer_ = self._editor.textview.get_buffer()
        buffer_.cut_clipboard(self._get_clipboard(), True)

    def on_clipboard_paste(self, *args):
        if not self._editor:
            return
        buffer_ = self._editor.textview.get_buffer()
        buffer_.paste_clipboard(self._get_clipboard(), None, True)


    def on_commit(self, *args):
        if not self._editor:
            return
        gobject.idle_add(self._editor.commit)

    def on_connection_menu_activate(self, menuitem):
        widgets.rebuild_connection_menu(menuitem.get_submenu(), self,
                                        self.get_active_editor())

    def on_connection_notify(self, connection, property):
        if property.name == 'transaction-state':
            value = connection.get_property(property.name)
            gobject.idle_add(self.set_transaction_state, value, connection)

    def on_datasource_manager(self, *args):
        dlg = DatasourceManager(self)
        dlg.run()
        dlg.destroy()

    def on_editor_buffer_dirty(self, editor, param):
        if param.name == 'buffer-dirty':
            action = self._get_action('file-save')
            action.set_sensitive(editor.get_property(param.name))
            action = self._get_action('file-save-as')
            action.set_sensitive(editor.get_property(param.name))

    def on_editor_close(self, *args):
        editor = self.get_active_editor()
        if editor is not None:
            editor.close()

    def on_editor_connection_changed(self, editor, connection):
        if self._tracked_conn:
            sig = self._tracked_conn.get_data('cf::mainwin::notify')
            if sig:
                self._tracked_conn.disconnect(sig)
            self._tracked_conn = None
        for group in self.ui.get_action_groups():
            if group.get_name() == 'query':
                group.set_sensitive(connection is not None)
        if connection:
            self.set_title(connection.get_label()+' - CrunchyFrog')
        else:
            self.set_title('CrunchyFrog %s' % release.version)
        # Set transaction state
        if connection:
            self._tracked_conn = connection
            sig = self._tracked_conn.connect('notify',
                                             self.on_connection_notify)
            self._tracked_conn.set_data('cf::mainwin::notify', sig)
            state = connection.get_property('transaction-state')
            self.set_transaction_state(state, connection)

    def on_editor_disconnect(self, action):
        editor = self.get_active_editor()
        if editor is None or editor.connection is None:
            return
        editor.set_connection(None)

    def on_editor_new(self, *args):
        editor = self.editor_create()
        # FIXME(andi): Updating editor switcher action should be in a
        #              separate function.
        self.on_query_menu_activate(None)

    def on_editor_print(self, action):
        self.get_active_editor().print_contents()

    def on_editor_print_preview(self, action):
        self.get_active_editor().print_contents(preview=True)

    def on_editor_set_focus(self, first_action, current):
        queries_idx = current.get_current_value()
        if queries_idx == -1:
            queries_idx = 9
        if self.queries.get_n_pages()-1 < queries_idx:
            return
        self.queries.set_current_page(queries_idx)
        editor = self.queries.get_nth_page(queries_idx)
        editor.get_child1().get_children()[0].grab_focus()

    def on_frmt_comment(self, action):
        editor = self.get_active_editor()
        if editor is None:
            return
        editor.selected_lines_toggle_comment()

    def on_file_save(self, *args):
        editor = self.get_active_editor()
        if editor is None:
            return
        editor.save_file(self)

    def on_file_save_as(self, *args):
        editor = self.get_active_editor()
        if editor is None:
            return
        editor.save_file_as(self)

    def on_instance_new(self, action):
        self.app.new_instance()

    def on_menu_item_deselect(self, menuitem):
        self.statusbar.pop(100)

    def on_menu_item_select(self, menuitem, tooltip):
        self.statusbar.push(100, tooltip)

    def on_open_file(self, *args):
        dlg = gtk.FileChooserDialog(_(u"Select file"),
                            self,
                            gtk.FILE_CHOOSER_ACTION_OPEN,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                             gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dlg.set_current_folder(self.app.config.get("editor.recent_folder", ""))
        dlg.set_select_multiple(True)
        filter = gtk.FileFilter()
        filter.set_name(_(u"All files (*)"))
        filter.add_pattern("*")
        dlg.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name(_(u"SQL files (*.sql)"))
        filter.add_pattern("*.sql")
        dlg.add_filter(filter)
        dlg.set_filter(filter)
        recent_chooser = gtk.RecentChooserWidget(self.app.recent_manager)
        filter = gtk.RecentFilter()
        filter.add_mime_type("text/x-sql")
        filter.set_name(_(u"SQL files (*.sql)"))
        recent_chooser.add_filter(filter)
        recent_chooser.set_filter(filter)
        recent_chooser.set_show_not_found(False)
        recent_chooser.set_sort_type(gtk.RECENT_SORT_MRU)
        recent_chooser.set_show_icons(True)
        recent_chooser.set_show_tips(True)
        def dlg_set_uri(chooser, dlg):
            if chooser.get_current_uri():
                dlg.set_uri(chooser.get_current_uri())
        recent_chooser.connect("selection-changed", dlg_set_uri, dlg)
        recent_chooser.connect("item-activated",
                               lambda chooser: dlg.response(gtk.RESPONSE_OK))
        exp = gtk.Expander(_(u"_Recent files:"))
        exp.add(recent_chooser)
        exp.set_use_underline(True)
        dlg.set_extra_widget(exp)
        recent_chooser.show()
        if dlg.run() == gtk.RESPONSE_OK:
            [self.editor_create(fname) for fname in dlg.get_filenames()]
            self.app.config.set("editor.recent_folder",
                                dlg.get_current_folder())
        dlg.destroy()

    def on_preferences(self, *args):
        self.app.preferences_show()

    def on_query_execute(self, *args):
        self.get_active_editor().execute_query()

    def on_query_menu_activate(self, menuitem):
        for idx in range(1, 11):
            if idx == 10:
                idx = 0
                page_idx = 9
            else:
                page_idx = idx - 1
            action = self._get_action('activate-editor%d' % idx)
            page = self.queries.get_nth_page(page_idx)
            if page is None:
                action.set_visible(False)
                action.set_sensitive(False)
            else:
                action.set_visible(True)
                action.set_sensitive(True)
                tab = self.queries.get_tab_label(page)
                lbl = tab.label.get_text()
                if len(lbl) > 16:
                    lbl = lbl[:15]+'...'
                action.props.label = lbl.replace('_', '__')
                is_active = bool(page_idx == self.queries.get_current_page())
                action.set_active(is_active)

    def on_quit(self, *args):
        if not self.close_all_editors():
            return False
        if len(self.app.get_instances()) <= 1:
            self.state_save()
        self.destroy()

    def on_recent_item_activated(self, chooser):
        self.editor_create(chooser.get_current_uri())

    def on_rollback(self, *args):
        if not self._editor:
            return
        gobject.idle_add(self._editor.rollback)

    def on_set_paned_position(self, win, paned):
        if isinstance(paned, gtk.VPaned):
            opt = 'win.bottompane_position'
        else:
            opt = 'win.sidepane_position'
        w, h = win.get_size()
        stored_pos = self.app.config.get(opt, None)
        if stored_pos is None:
            if isinstance(paned, gtk.VPaned):
                stored_pos = h-250
            else:
                stored_pos = 250
        paned.set_position(stored_pos)
        paned.connect('notify::position',
                      lambda paned, prop:
                      self.app.config.set(opt, paned.get_position()))

    def on_toggle_statusbar(self, toggle_action):
        if toggle_action.get_active():
            self.statusbar.show()
        else:
            self.statusbar.hide()
        self.app.config.set('win.statusbar_visible',
                            toggle_action.get_active())

    def on_toggle_toolbar(self, toggle_action):
        if toggle_action.get_active():
            self.toolbar.show()
        else:
            self.toolbar.hide()
        self.app.config.set('win.toolbar_visible',
                            toggle_action.get_active())

    def on_ui_connect_proxy(self, ui, action, widget):
        tooltip = action.get_property('tooltip')
        if isinstance(widget, gtk.MenuItem) and tooltip:
            cid = widget.connect('select', self.on_menu_item_select, tooltip)
            cid2 = widget.connect('deselect', self.on_menu_item_deselect)
            widget.set_data('cf::cids', (cid, cid2))

    def on_ui_disconnect_proxy(self, ui, action, widget):
        cids = widget.get_data('cf::cids') or ()
        for name, cid in cids:
            widget.disconect(cid)

    def on_window_state_event(self, window, event):
        val_names = event.new_window_state.value_names
        c = self.app.config
        c.set('gui.maximized',
              gtk.gdk.WINDOW_STATE_MAXIMIZED.value_names[0] in val_names)

    # ---
    # Public methods
    # ---

    def close_all_editors(self):
        """Closes all editors but checks for changes first.

        Returns:
          False if action was cancelled, otherwise True.
        """
        changed = []
        for item in self.queries.get_all_editors():
            if isinstance(item, Editor) and item.contents_changed():
                changed.append(item)
        if changed:
            dlg = ConfirmSaveDialog(self, changed)
            proceed = dlg.run()
            if proceed == 1:
                dlg.hide()
                if not dlg.save_files():
                    proceed = 0
            dlg.destroy()
            if proceed == 0:
                return False
        for item in self.queries.get_all_editors():
            item.close(force=True)
        return True

    def editor_create(self, fname=None):
        """Creates a new SQL editor.

        Arguments:
          fname: If given, the file fname is opened with this editor.

        Returns:
          An Editor instance.
        """
        last_conn = None
        if self.app.config.get('editor.reuse_connection'):
            cur_editor = self.get_active_editor()
            if cur_editor is not None:
                last_conn = cur_editor.get_connection()
        editor = Editor(self)
        if last_conn is not None:
            editor.set_connection(last_conn)
        if fname:
            if fname.startswith("file://") and HAVE_GNOMEVFS:
                fname = gnomevfs.get_local_path_from_uri(fname)
            editor.set_filename(fname)
        self.editor_append(editor)
        editor.show_all()
        editor.textview.grab_focus()
        return editor

    def editor_append(self, editor):
        """Adds an editor to the editors notebook.

        Arguments:
          editor: Editor instance.
        """
        # Cleanup other instances
        for instance in self.app.get_instances():
            if instance != self and editor in instance._editors:
                instance._editors.remove(editor)
        self.queries.add_item(editor)
        self._editors.append(editor)

    def get_active_editor(self):
        """Returns the active editor.

        Returns:
          Editor instance or None.
        """
        return self._editor

    def set_editor_active(self, editor, active):
        """Called whenever an editor receives or looses focus."""
        if not active:
            editor = None
        if self._editor_conn_tag and self._editor:
            self._editor.disconnect(self._editor_conn_tag)
            self._editor_conn_tag = None
        if self._editor:
            handler_id = self._editor.get_data('cf::sig_editor_buffer_dirty')
            if handler_id:
                self._editor.disconnect(handler_id)
                self._editor.set_data('cf::sig_editor_buffer_dirty', None)
            handler_id = self._editor.get_data('cf::sig_editor_buffer_changed')
            if handler_id:
                self._editor.disconnect(handler_id)
                self._editor.set_data('cf::sig_editor_buffer_changed', None)
        self._editor = editor
        if self._editor and isinstance(self._editor, Editor):
            self._editor_conn_tag = self._editor.connect(
                "connection-changed", self.on_editor_connection_changed)
            self.on_editor_connection_changed(
                self._editor, self._editor.connection)
            conn = self._editor.connection
            if conn:
                prop =conn.get_property('transaction-state')
                self.set_transaction_state(prop, conn)
            handler_id = self._editor.connect('notify::buffer-dirty',
                                              self.on_editor_buffer_dirty)
            self._editor.set_data('cf::sig_editor_buffer_dirty', handler_id)
            # XXX add buffer selection changed cb to update copy&paste btns
        else:
            self.set_title('CrunchyFrog %s' % release.version)
        for group in self.ui.get_action_groups():
            if group.get_name() == 'editor':
                group.set_sensitive(self._editor is not None)
                break
        sensitive = bool((self._editor
                          and isinstance(self._editor, Editor)
                          and self._editor.props.buffer_dirty))
        action = self._get_action('file-save')
        action.set_sensitive(sensitive)
        action = self._get_action('file-save-as')
        action.set_sensitive(sensitive)
        self.tb_conn_chooser.set_editor(editor)
        self.app.plugins.editor_notify(editor, self)
        self.emit('active-editor-changed', editor)
        if editor is not None and isinstance(editor, Editor):
            editor.textview.grab_focus()

    def set_transaction_state(self, value, connection):
        """Adjusts the transactions state in the UI."""
        # A regression: If value is None that means we have no connection,
        # but this is already handled by setting the whole action group
        # insensitive.
        if value is None or connection is None:
            return
        commit = self._get_action('query-commit')
        rollback = self._get_action('query-rollback')
        begin = self._get_action('query-begin')
        if connection.provider.features.transactions:
            commit.set_sensitive((value & TRANSACTION_COMMIT_ENABLED) != 0)
            rollback.set_sensitive((value & TRANSACTION_ROLLBACK_ENABLED) != 0)
            begin.set_sensitive((value & TRANSACTION_IDLE) != 0)
        else:
            commit.set_sensitive(False)
            rollback.set_sensitive(False)
            begin.set_sensitive(False)

    def state_restore(self):
        """Restore window state."""
        conf = self.app.config
        action = self._get_action('instance-toggle-statusbar')
        action.set_active(conf.get('win.statusbar_visible', True))
        self.on_toggle_statusbar(action)
        action = self._get_action('instance-toggle-toolbar')
        action.set_active(conf.get('win.toolbar_visible', True))
        self.on_toggle_toolbar(action)
        self.side_pane.state_restore()
        self.bottom_pane.state_restore()
        self.resize(conf.get('gui.width', 650),
                    conf.get('gui.height', 650))
        if conf.get('gui.maximized', False):
            self.maximize()
        fname = os.path.join(USER_CONFIG_DIR, 'shortcuts.map')
        if os.path.isfile(fname):
            gtk.accel_map_load(fname)

    def state_save(self):
        """Save window state to config."""
        c = self.app.config
        w, h = self.get_size()
        c.set('gui.width', w)
        c.set('gui.height', h)
        for pane in [self.side_pane, self.bottom_pane]:
            c.set('win.%s_visible' % pane.__class__.__name__.lower(),
                  pane.get_property('visible'))
        fname = os.path.join(USER_CONFIG_DIR, 'shortcuts.map')
        gtk.accel_map_save(fname)

gobject.type_register(MainWindow)


# NOTE: All menu actions MUST end with *-menu-action. That's needed by
#       the preferences dialog to filter out some actions.
#       Maybe there's a better way to do it, but it works... ;-)

UI = '''
  <menubar name="MenuBar">
    <menu name="File" action="file-menu-action">
      <menu name="FileNew" action="file-new-menu-action">
        <menuitem name="NewEditor" action="instance-new-editor" />
        <menuitem name="NewInstance" action="instance-new-mainwin" />
      </menu>
      <menuitem name="Open" action="file-open" />
      <menuitem name="Save" action="file-save" />
      <menuitem name="SaveAs" action="file-save-as" />
      <placeholder name="RecentFiles" />
      <separator />
      <menuitem name="Print" action="editor-print" />
      <menuitem name="PrintPreview" action="editor-printpreview" />
      <separator />
      <menuitem name="Close" action="editor-close" />
      <menuitem name="CloseAll" action="editor-close-all" />
      <menuitem name="Quit" action="instance-quit" />
    </menu>
    <menu name="Edit" action="edit-menu-action">
      <menuitem name="Cut" action="clipboard-cut" />
      <menuitem name="Copy" action="clipboard-copy" />
      <menuitem name="Paste" action="clipboard-paste" />
      <separator />
      <menuitem name="Plugins" action="instance-plugins" />
      <menuitem name="Datasources" action="instance-datasourcemanager" />
      <menuitem name="Preferences" action="instance-preferences" />
    </menu>
    <menu name="View" action="view-menu-action">
      <menuitem name="Toolbar" action="instance-toggle-toolbar" />
      <menuitem name="Statusbar" action="instance-toggle-statusbar" />
    </menu>
    <menu name="Query" action="query-menu-action">
      <menu name="Connection" action="query-connection-menu-action">
        <separator />
        <menuitem name="Disconnect" action="query-connection-disconnect" />
        <menuitem name="Connections" action="query-show-connections" />
      </menu>
      <separator />
      <menuitem name="Execute" action="query-execute" />
      <menuitem name="Begin" action="query-begin" />
      <menuitem name="Commit" action="query-commit" />
      <menuitem name="Rollback" action="query-rollback" />
      <separator />
      <menu name="QueryFormat" action="query-frmt-menu">
        <menuitem name="QueryFormatComment" action="query-frmt-comment" />
      </menu>
      <placeholder name="query-extensions" />
      <separator />
      <menuitem name="Editor1" action="activate-editor1" />
      <menuitem name="Editor2" action="activate-editor2" />
      <menuitem name="Editor3" action="activate-editor3" />
      <menuitem name="Editor4" action="activate-editor4" />
      <menuitem name="Editor5" action="activate-editor5" />
      <menuitem name="Editor6" action="activate-editor6" />
      <menuitem name="Editor7" action="activate-editor7" />
      <menuitem name="Editor8" action="activate-editor8" />
      <menuitem name="Editor9" action="activate-editor9" />
      <menuitem name="Editor0" action="activate-editor0" />
    </menu>
    <menu name="Help" action="help-menu-action">
      <menuitem name="HelpHelp" action="help-help" />
      <separator />
      <menuitem name="HelpTranslate" action="help-translate" />
      <menuitem name="HelpBugs" action="help-bugs" />
      <menuitem name="HelpAbout" action="help-about" />
    </menu>
  </menubar>
  <toolbar name="ToolBar">
    <toolitem name="NewEditor" action="instance-new-editor" />
    <placeholder name="OpenFile" action="instance-open-file" />
    <toolitem name="SaveFile" action="file-save" />
    <separator />
    <placeholder name="EditorConnection" />
    <separator />
    <toolitem name="QueryExecute" action="query-execute" />
    <toolitem name="QueryBegin" action="query-begin" />
    <toolitem name="QueryCommit" action="query-commit" />
    <toolitem name="QueryRollback" action="query-rollback" />
  </toolbar>
'''
