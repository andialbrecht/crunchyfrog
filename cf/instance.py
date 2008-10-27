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

# $Id$

"""Instance class"""

from gettext import gettext as _
import os

import gnome
import gnomevfs
import gobject
import gtk
import gtk.glade

from cf import release
from cf.ui import GladeWidget
from cf.ui import pdock
from cf.ui.browser import Browser
from cf.ui.confirmsave import ConfirmSaveDialog
from cf.ui.datasources import DatasourceManager
from cf.ui.editor import Editor, EditorWindow
from cf.ui.queries import QueriesNotebook
from cf.ui.statusbar import CFStatusbar
from cf.ui.toolbar import CFToolbar
from cf.ui.widgets import ConnectionButton


class CFInstance(GladeWidget):

    def __init__(self, app):
        """Constructor.

        Args:
          app: CFApplication instance.
        """
        GladeWidget.__init__(self, app, "crunchyfrog", "mainwindow")
        self._editor = None
        self._editor_conn_tag = None
        self._editors = list()

    def _setup_widget(self):
        # Window state
        if self.app.config.get("gui.width", -1) != -1:
            self.widget.resize(self.app.config.get("gui.width"),
                               self.app.config.get("gui.height"))
        if self.app.config.get("gui.maximized", False):
            self.widget.maximize()
        # Tooltips
        self.tt = gtk.Tooltips()
        # Toolbar
        self.toolbar = CFToolbar(self)
        self.toolbar.show_all()
        # Statusbar
        self.statusbar = CFStatusbar(self.app, self.xml)
        # Dock
        self.dock = pdock.Dock()
        box = self.xml.get_widget("box_main")
        box.pack_start(self.dock, True, True)
        box.reorder_child(self.dock, 2)
        self.dock.show_all()
        # Queries
        self.queries = QueriesNotebook(self.app, self)
        item = pdock.DockItem(self.dock, "queries",
                              self.queries, _(u"Queries"),
                              "gtk-edit", None, pdock.DOCK_ITEM_BEH_LOCKED)
        self.dock.add_item(item)
        # Browser
        self.browser = Browser(self.app, self)
        item = pdock.DockItem(self.dock, "browser",
                              self.browser, _(u"Navigator"),
                              "gtk-find", gtk.POS_LEFT,
                              pdock.DOCK_ITEM_BEH_CANT_CLOSE)
        self.dock.add_item(item)
        self.browser.set_data("dock_item", item)
        gobject.idle_add(self.xml.get_widget("mn_navigator").set_active,
                         self.app.config.get("navigator.visible", True))
        # Menu bar
        recent_menu = gtk.RecentChooserMenu(self.app.recent_manager)
        filter = gtk.RecentFilter()
        filter.add_mime_type("text/x-sql")
        recent_menu.add_filter(filter)
        recent_menu.set_filter(filter)
        recent_menu.set_show_not_found(False)
        recent_menu.set_sort_type(gtk.RECENT_SORT_MRU)
        recent_menu.connect("item-activated", self.on_recent_item_activated)
        recent_item = self.xml.get_widget("mn_recent")
        recent_item.set_submenu(recent_menu)

    def _init_ui(self, argv):
        pass

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
        dlg.set_logo_icon_name(release.appname)
        dlg.set_program_name(release.appname)
        dlg.set_translator_credits(release.translators)
        dlg.run()
        dlg.destroy()

    def on_commit(self, *args):
        if not self._editor:
            return
        gobject.idle_add(self._editor.commit)

    def on_rollback(self, *args):
        if not self._editor:
            return
        gobject.idle_add(self._editor.rollback)

    def on_begin_transaction(self, *args):
        if not self._editor:
            return
        gobject.idle_add(self._editor.begin_transaction)

    def on_configure_event(self, win, event):
        config = self.app.config
        if not config.get("gui.maximized"):
            config.set("gui.width", event.width)
            config.set("gui.height", event.height)

    def _get_clipboard(self):
        display = gtk.gdk.display_manager_get().get_default_display()
        return gtk.Clipboard(display, "CLIPBOARD")

    def on_copy(self, *args):
        if not self._editor:
            return
        buffer_ = self._editor.textview.get_buffer()
        buffer_.copy_clipboard(self._get_clipboard())

    def on_paste(self, *args):
        if not self._editor:
            return
        buffer_ = self._editor.textview.get_buffer()
        buffer_.paste_clipboard(self._get_clipboard(), None, True)

    def on_cut(self, *args):
        if not self._editor:
            return
        buffer_ = self._editor.textview.get_buffer()
        buffer_.cut_clipboard(self._get_clipboard(), True)

    def on_recent_item_activated(self, chooser):
        self.new_editor(chooser.get_current_uri())

    def on_delete(self, *args):
        if not self._editor:
            return
        buffer_ = self._editor.textview.get_buffer()
        buffer_.delete_selection(True, True)

    def on_datasource_manager(self, *args):
        dlg = DatasourceManager(self.app, self)
        dlg.run()
        dlg.destroy()

    def on_editor_connection_changed(self, editor, connection):
        if connection:
            self.set_title(connection.get_label()+" - CrunchyFrog")
        else:
            self.set_title("CrunchyFrog")

    def on_execute_query(self, *args):
        gobject.idle_add(self._editor.execute_query)

    def on_help(self, *args):
        self.show_help()

    def on_navigator_toggled(self, menuitem):
        if menuitem.get_active():
            self.browser.get_data("dock_item").show()
            self.app.config.set("navigator.visible", True)
        else:
            self.browser.get_data("dock_item").hide()
            self.app.config.set("navigator.visible", False)

    def on_new_instance(self, *args):
        self.app.new_instance(tuple())

    def on_open_file(self, *args):
        dlg = gtk.FileChooserDialog(_(u"Select file"),
                            self.widget,
                            gtk.FILE_CHOOSER_ACTION_OPEN,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                             gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dlg.set_current_folder(self.app.config.get("editor.recent_folder", ""))
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
            self.new_editor(dlg.get_filename())
            self.app.config.set("editor.recent_folder",
                                dlg.get_current_folder())
        dlg.destroy()

    def on_save_file(self, *args):
        if not self._editor:
            return
        self._editor.save_file()

    def on_save_file_as(self, *args):
        if not self._editor:
            return
        self._editor.save_file_as()

    def on_report_problem(self, *args):
        gobject.idle_add(self.open_website,
                         "http://code.google.com/p/crunchyfrog/issues/list")

    def on_open_devpages(self, *args):
        gobject.idle_add(self.open_website, "http://cf.andialbrecht.de")

    def on_open_helptranslate(self, *args):
        gobject.idle_add(self.open_website,
                         ("https://translations.launchpad.net/"
                          "crunchyfrog/trunk/"))

    def on_preferences(self, *args):
        self.app.preferences_show()

    def on_plugins_configure(self, *args):
        self.app.preferences_show("plugins")

    def on_query_new(self, *args):
        self.new_editor()

    def on_quit(self, *args):
        if not self.check_unsaved_changes():
            return
        self.widget.destroy()

    def on_window_state_event(self, win, event):
        config = self.app.config
        val_names = event.new_window_state.value_names
        config.set("gui.maximized",
                   gtk.gdk.WINDOW_STATE_MAXIMIZED.value_names[0] in val_names)

    def new_editor(self, fname=None):
        """Creates a new SQL editor.

        Arguments:
          fname: If given, the file fname is opened with this editor.

        Returns:
          An Editor instance.
        """
        editor = Editor(self.app, self)
        if fname:
            if fname.startswith("file://"):
                fname = gnomevfs.get_local_path_from_uri(fname)
            editor.set_filename(fname)
        if self.app.config.get("editor.open_in_window"):
            editor.show_in_separate_window()
        else:
            self.queries.attach(editor)
        editor.show_all()
        self._editors.append(editor)
        return editor

    def check_unsaved_changes(self):
        changed_editors = list()
        for editor in self._editors:
            if editor.contents_changed():
                changed_editors.append(editor)
        if changed_editors:
            dlg = ConfirmSaveDialog(self, changed_editors)
            resp = dlg.run()
            if resp == 1:
                ret = dlg.save_files()
            elif resp == 2:
                ret = True
            else:
                ret = False
            dlg.destroy()
        else:
            ret = True
        return ret

    def open_website(self, url):
        gtk.show_uri(gtk.gdk.screen_get_default(), url, 0)

    def set_editor_active(self, editor, active):
        if not active:
            editor = None
        if self._editor_conn_tag and self._editor:
            self._editor.disconnect(self._editor_conn_tag)
            self._editor_conn_tag = None
        self._editor = editor
        if self._editor:
            self._editor_conn_tag = self._editor.connect(
                "connection-changed", self.on_editor_connection_changed)
            self.on_editor_connection_changed(
                self._editor, self._editor.connection)
        else:
            self.set_title("CrunchyFrog")
        self.toolbar.set_editor(editor)
        self.app.plugins.editor_notify(editor, self)

    def get_editor(self):
        """Returns the active editor.

        Returns:
          Editor instance or .None.
        """
        return self._editor

    def show_help(self, topic=None):
        gnome.help_display(release.appname, topic)


class InstanceSelector(GladeWidget):

    def __init__(self, client):
        self.client = client
        GladeWidget.__init__(self, None, "crunchyfrog", "instanceselector")

    def _setup_widget(self):
        model = gtk.ListStore(int, str)
        self.list = self.xml.get_widget("list_instances")
        self.list.set_model(model)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=1)
        self.list.append_column(col)
        for id, title in self.client.get_instances():
            model.append([id, title])

    def _setup_connections(self):
        sel = self.list.get_selection()
        sel.connect("changed", self.on_isel_changed)
        self.xml.get_widget("btn_newinstance").connect(
            "toggled", self.on_newi_toggled)

    def on_newi_toggled(self, btn):
        sel = self.list.get_selection()
        model = self.list.get_model()
        if btn.get_active():
            sel.unselect_all()
        else:
            sel.select_iter(model.get_iter_first())
        self.list.set_sensitive(not btn.get_active())

    def on_isel_changed(self, selection):
        model, iter = selection.get_selected()
        if not iter:
            self.xml.get_widget("btn_newinstance").set_active(True)
        else:
            self.xml.get_widget("btn_activeinstance").set_active(True)

    def get_instance_id(self):
        if self.xml.get_widget("btn_newinstance").get_active():
            return None
        else:
            sel = self.list.get_selection()
            model, iter = sel.get_selected()
            if iter:
                return model.get_value(iter, 0)
            return None
