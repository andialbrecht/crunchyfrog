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

"""Panes in the mainwindow"""

import logging
import os
import re
from gettext import gettext as _

import gobject
import gtk
import pango

from cf.ui import GladeWidget


try:
    # Let's see if we have additional items.
    # This is a dirty hack...
    it = gtk.icon_theme_get_default()
    info = it.load_icon('stock_book_green', gtk.ICON_SIZE_MENU,
                        gtk.ICON_LOOKUP_FORCE_SVG)
    HAVE_ICONS = True
except gobject.GError, err:
    # Some special icons are not present. Let's set HAVE_ICONS to False.
    # This causes the tab widgets to display the name of the pane item.
    # It's better than empty tab labels... ;-)
    logging.warning('Failed to load additional icons (%s)', err)
    HAVE_ICONS = False


# GTK style from GEdit's close button (gedit-notebook.c)
gtk.rc_parse_string('''style "cf-tab-button-style"
{
  GtkWidget::focus-padding = 0
  GtkWidget::focus-line-width = 0
  xthickness = 0
  ythickness = 0
}
widget "*.cf-tab-button" style "cf-tab-button-style"''')

TAB_LABEL_CENTER = 1
TAB_LABEL_SIDEPANE = 2


class PaneItem(object):
    name = None
    icon = None
    detachable = False

    def __init__(self, app):
        self._tab_label = None
        self.app = app

    @property
    def tab_label(self):
        return self.get_tab_label()

    def close(self, force=False):
        self.destroy()

    def get_tab_label(self):
        if self._tab_label is None:
            self._tab_label = TabLabelDefault(self.app, self)
        return self._tab_label

    def get_pane_icon(self):
        return gtk.STOCK_MISSING_IMAGE

    def get_pane_name(self):
        return '???'

    def get_pane_detachable(self):
        return False

    def get_focus_child(self):
        return None

    def get_widget(self):
        """Returns the real gtk.Widget that should be displayed."""
        return self


class Pane(object):
    """Base class for all pane widgets."""

    def __init__(self, mainwin):
        self.app = mainwin.app
        # TODO: Rename to self.instance
        self.mainwin = mainwin
        self._merge_ui()
        self.header = gtk.HBox()
        self.header.set_spacing(5)
        self.header.set_border_width(7)
        self.top_img = gtk.Image()
        self.header.pack_start(self.top_img, False, False)
        self.top_img.show()
        self.top_label = gtk.Label()
        self.top_label.set_alignment(0, 0.5)
        self.header.pack_start(self.top_label)
        self.top_label.show()
        self.top_btn = gtk.Button()
        self.top_btn.add(gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_NONE))
        self.top_btn.set_relief(gtk.RELIEF_NONE)
        self.top_btn.connect('button-press-event', self.on_top_btn_clicked)
        self.header.pack_start(self.top_btn, False, False)
        self.top_btn.show_all()
        self.pack_start(self.header, False, False)
        self.header.show()
        self.notebook = gtk.Notebook()
        self.notebook.set_tab_pos(gtk.POS_BOTTOM)
        self.notebook.set_scrollable(True)
        self.pack_start(self.notebook, True, True)
        self.notebook.show()
        self._autohide_tabs = False
        self.notebook.connect('switch-page', self.on_notebook_switch_page)
        self.notebook.connect('page-added',
                              self.on_notebook_pages_changed, 'added')
        self.notebook.connect('page-removed',
                              self.on_notebook_pages_changed, 'removed')
        self.notebook.set_group_id(99)
        self.hide()
        self._state_restored = False

    def _merge_ui(self):
        ui = self.mainwin.ui
        for group in ui.get_action_groups():
            if group.get_name() == 'instance':
                group.add_toggle_actions(self.get_action_entries())
        ui_desc = self.get_ui_description()
        if ui_desc:
            self.mainwin.ui.add_ui_from_string(ui_desc)
            self.mainwin.ui.ensure_update()

    def _restore(self):
        action_name = 'instance-toggle-%s' % self.__class__.__name__.lower()
        conf_name = 'win.%s_visible' % self.__class__.__name__.lower()
        action = self.mainwin._get_action(action_name)
        action.set_active(self.app.config.get(conf_name, True))
        self.on_toggle(action)

    def on_move_page(self, menuitem, page, pane):
        pane.add_item(page)

    def on_notebook_pages_changed(self, nb, page, page_num, action_str):
        if self._autohide_tabs:
            nb.set_show_tabs(nb.get_n_pages() > 1)
            nb.set_show_border(nb.get_n_pages() > 1)
        if not self._state_restored:  # don't do anything before state restored
            return
        action_name = 'instance-toggle-%s' % self.__class__.__name__.lower()
        action = self.mainwin._get_action(action_name)
        if nb.get_n_pages() == 0:
            self.hide()
            action.set_active(False)
            action.set_sensitive(False)
        else:
            if not action.get_sensitive():
                action.set_sensitive(True)
                if action.get_active():
                    self.show()
            visopt = 'win.%s_visible' % self.__class__.__name__.lower()
            if self.app.config.get(visopt, False) and nb.get_n_pages():
                action.set_active(True)

    def on_notebook_switch_page(self, nb, unusable, page_num):
        page = nb.get_nth_page(page_num)
        if page.get_data('cf::real-object'):
            page = page.get_data('cf::real-object')
        self.top_label.set_text(page.name)
        pb = self.app.load_icon(page.icon, gtk.ICON_SIZE_MENU,
                                gtk.ICON_LOOKUP_FORCE_SVG)
        self.top_img.set_from_pixbuf(pb)

    def on_page_detach(self, menuitem, page):
        alloc = page.get_allocation()
        def attach(window, page):
            self.add_item(page)
        w = gtk.Window()
        w.resize(alloc.width, alloc.height)
        w.set_transient_for(self.mainwin)
        w.connect('destroy', attach, page)
        page.reparent(w)
        w.set_title(page.name)
        w.set_icon_name(page.icon)
        w.show()

    def on_toggle(self, toggle_action):
        if toggle_action.get_active():
            self.show()
        else:
            self.hide()

    def on_top_btn_clicked(self, btn, event):
        menu = gtk.Menu()
        action_name = 'instance-toggle-%s' % self.__class__.__name__.lower()
        action = self.mainwin._get_action(action_name)
        item = action.create_menu_item()
        menu.append(item)
        item.show()
        page = self.notebook.get_nth_page(self.notebook.get_current_page())
        if page.detachable:
            item = gtk.MenuItem(_(u'Detach %(name)s') % {'name': page.name})
            item.connect('activate', self.on_page_detach, page)
            menu.append(item)
            item.show()
            if self.__class__.__name__.startswith('Bottom'):
                other_pane = _(u'side pane')
                other = self.mainwin.side_pane
            else:
                other_pane = _(u'bottom pane')
                other = self.mainwin.bottom_pane
            item = gtk.MenuItem(_(u'Move to %(name)s') % {'name': other_pane})
            item.connect('activate', self.on_move_page, page, other)
            item.show()
            menu.append(item)
        menu.popup(None, None, None, event.button, event.time)

    def get_action_entries(self):
        raise NotImplementedError

    def get_ui_description(self):
        return self.UI_DESCRIPTION

    def add_item(self, item):
        """Add a PaneItem."""
        assert isinstance(item, PaneItem)
        pitem = item
        item = pitem.get_widget()
        item.set_data('cf::real-object', pitem)
        tab_label = pitem.get_tab_label()
        if self.__class__.__name__ != 'CenterPane':
            tab_label.set_mode(TAB_LABEL_SIDEPANE)
        if item.get_parent():
            item.reparent(self.notebook)
            self.notebook.set_tab_label(item, tab_label)
        else:
            self.notebook.append_page(item, tab_label)
        self.notebook.set_tab_detachable(item, True)
        item.show()
        tab_label.show()

    def remove_item(self, pane_item):
        """Remove a previously added PaneItem."""
        raise NotImplementedError

    def set_active_item(self, item_id):
        """Toggle the active/visible item."""
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            if page.item_id == item_id:
                self.notebook.set_current_page(i)
                return

    def set_autohide_tabs(self, autohide):
        """Enable/disable tab autohide."""
        self._autohide_tabs = autohide

    def set_hidden(self, hidden):
        """Hide/show the pane."""
        raise NotImplementedError

    def set_show_header(self, visible):
        """Show or hide the header."""
        if visible:
            self.header.show()
        else:
            self.header.hide()

    def state_restore(self):
        """Restore last UI state."""
        self._restore()
        self._state_restored = True
        self.on_notebook_pages_changed(self.notebook, None, 0, 'removed')


class SidePane(gtk.VBox, Pane):

    UI_DESCRIPTION = '''<menubar name="MenuBar">
      <menu name="View" action="view-menu-action">
        <menuitem name="SidePane" action="instance-toggle-sidepane" />
      </menu>
    </menubar>'''

    def __init__(self, mainwin):
        gtk.VBox.__init__(self)
        Pane.__init__(self, mainwin)

    def get_action_entries(self):
        return (
            ('instance-toggle-sidepane', None,
             _(u'Side _Pane'), 'F9',
             _(u'Show or hide the side pane in the current window'),
             self.on_toggle),
        )


class BottomPane(gtk.VBox, Pane):

    UI_DESCRIPTION = '''<menubar name="MenuBar">
      <menu name="View" action="view-menu-action">
        <menuitem name="BottomPane" action="instance-toggle-bottompane" />
      </menu>
    </menubar>'''

    def __init__(self, mainwin):
        gtk.VBox.__init__(self)
        Pane.__init__(self, mainwin)
        self.notebook.set_tab_pos(gtk.POS_RIGHT)

    def get_action_entries(self):
        return (
            ('instance-toggle-bottompane', None,
             _(u'_Bottom Pane'), '<control>F9',
             _(u'Show or hide the bottom pane in the current window'),
             self.on_toggle),
        )


class CenterPane(gtk.VBox, Pane):

    UI_DESCRIPTION = None

    def __init__(self, mainwin):
        gtk.VBox.__init__(self)
        Pane.__init__(self, mainwin)
        self.set_autohide_tabs(False)
        self.set_show_header(False)
        self.notebook.set_scrollable(True)
        self.notebook.set_tab_pos(gtk.POS_TOP)
        self.notebook.popup_disable()
        self.notebook.set_show_tabs(True)
        self.notebook.set_show_border(True)
        self.notebook.set_property("enable-popup", False)
        self.notebook.connect("switch-page", self.on_switch_page)
        self.notebook.connect("page-removed", self.on_page_removed)
        self.notebook.set_group_id(1)
        self.notebook.connect('create-window', self.on_create_window)

    def on_create_window(self, nb, page, x, y):
        view = self.get_view_by_page(page)
        view.detach()

    def on_page_added(self, notebook, child, page_num):
        gobject.idle_add(self.notebok.set_current_page, page_num)

    def on_page_removed(self, notebook, child, page_num):
        from cf.ui.editor import Editor  # import hook
        if isinstance(child, Editor):
            self.mainwin.set_editor_active(child, False)

    def on_switch_page(self, notebook, page, page_num):
        editor = self.get_nth_page(page_num).get_data('cf::real-object')
        gobject.idle_add(self.mainwin.set_editor_active, editor, True)

    def add_item(self, editor):
        super(CenterPane, self).add_item(editor)
        from cf.ui.editor import Editor
        if isinstance(editor, Editor):
            widget = editor.widget
            self.notebook.set_tab_label(widget, TabLabel(editor))
        else:
            widget = getattr(editor, 'widget', editor)  # LDAP hack
        self.notebook.set_tab_reorderable(widget, True)
        self.notebook.set_tab_detachable(widget, True)
        self.notebook.set_current_page(self.notebook.page_num(widget))
        self.mainwin._rebuild_activate_editor_actions()
        widget.connect('destroy', lambda *a:
                       self.mainwin._rebuild_activate_editor_actions())

    def get_all_editors(self):
        """Return a list of all editors."""
        ret = []
        for i in range(self.notebook.get_n_pages()):
            ret.append(self.get_view_by_pagenum(i))
        return ret

    def __getattribute__(self, name):
        """We want it to behave much like a gtk.Notebook."""
        try:
            attr = super(CenterPane, self).__getattribute__(name)
        except AttributeError:
            attr = getattr(self.notebook, name)
        return attr

    def get_action_entries(self):
        return []

    def get_view_by_pagenum(self, page_num):
        """Return editor object by page number."""
        child = self.notebook.get_nth_page(page_num)
        return self.get_view_by_page(child)

    def get_view_by_page(self, page):
        """Return editor object by child widget."""
        lbl = self.notebook.get_tab_label(page)
        return lbl.pane_item


class TabLabelDefault(gtk.HBox):
    """Default tab label implementation for pane items."""

    def __init__(self, app, pane_item, mode=TAB_LABEL_CENTER):
        """Constructor.

        :param pane_item: A :class:`PaneItem` instance.
        """
        gtk.HBox.__init__(self)
        self.app = app
        self.pane_item = pane_item
        self.mode = None
        self.datasource = None

        self.set_spacing(4)

        # Data source color indicator
        self.datasource_color_eb = gtk.EventBox()
        self.datasource_color_eb.set_size_request(5, -1)
        self.datasource_color_eb.show()
        self.pack_start(self.datasource_color_eb, False, False)

        # Icon
        pb = self.app.load_icon(self.pane_item.icon, gtk.ICON_SIZE_MENU,
                                gtk.ICON_LOOKUP_FORCE_SVG)
        self.img = gtk.image_new_from_pixbuf(pb)
        self.img.set_tooltip_text(self.pane_item.name)
        self.img.show()
        self.pack_start(self.img, False, False)

        # Label
        self.label = gtk.Label(_(u"Query"))
        self.label.set_ellipsize(pango.ELLIPSIZE_END)
        self.label.set_width_chars(15)
        self.label.set_single_line_mode(True)
        self.label.set_alignment(0, 0.5)
        # use a slightly smaller font in tabs like Empathy does...
        font_desc = self.label.get_style().font_desc
        font_desc.set_size(int(font_desc.get_size()*.8))
        self.label.modify_font(font_desc)
        self.label.show()
        self.pack_start(self.label, True, True)

        # Close button
        self.btn_close = gtk.Button()
        self.btn_close.set_focus_on_click(False)
        self.btn_close.set_relief(gtk.RELIEF_NONE)
        self.btn_close.set_name('cf-tab-button')
        image = gtk.image_new_from_stock(gtk.STOCK_CLOSE,
                                         gtk.ICON_SIZE_MENU)
        self.btn_close.add(image)
        self.btn_close.set_tooltip_text(_(u'Close'))
        self.btn_close.connect("clicked", self.on_button_close_clicked)
        self.btn_close.show_all()
        self.pack_start(self.btn_close, False, False)

        self.app.datasources.connect('datasource-changed',
                                     self.on_datasource_changed)

        self.set_mode(mode)

    def on_button_close_clicked(self, button):
        self.pane_item.close()

    def on_datasource_changed(self, manager, datasource):
        if datasource == self.datasource:
            self.set_datasource(datasource)

    def set_close_callback(self, callback):
        """Set a callback function that handles a click on the close button.

        The callback function has the signature ``def callback(tab_label)``.
        """
        assert (hasattr(callback, '__call__') or callback is None)
        self._close_cb = callback

    def set_datasource(self, datasource=None):
        """Set data source information.

        Usually this just updates the data source's color code.

        :param datasource: A :class:`~cf.db.Datasource` instance or ``None``.
        """
        if datasource is not None and datasource.color:
            color = gtk.gdk.color_parse(datasource.color)
            self.datasource_color_eb.modify_bg(gtk.STATE_NORMAL, color)
            self.datasource_color_eb.modify_bg(gtk.STATE_ACTIVE, color)
        else:
            self.datasource_color_eb.modify_bg(gtk.STATE_NORMAL, None)
            self.datasource_color_eb.modify_bg(gtk.STATE_ACTIVE, None)
        self.datasource = datasource

    def set_mode(self, mode):
        """Set tab label mode.

        *mode* is either ``TAB_LABEL_CENTER`` or ``TAB_LABEL_SIDEPANE``.
        """
        assert mode in (TAB_LABEL_CENTER, TAB_LABEL_SIDEPANE)
        self.mode = mode
        if self.mode == TAB_LABEL_CENTER:
            self.datasource_color_eb.show()
            self.label.show()
            self.btn_close.show()
        else:
            self.datasource_color_eb.hide()
            self.label.hide()
            self.btn_close.hide()

    def set_text(self, text):
        """Set tab label's text."""
        self.label.set_text(text)

    def set_tootltip(self, markup):
        """Set the tooltip for the whole tab label."""
        self.label.set_tooltip_markup(markup)
        self.datasource_color_eb.set_tooltip_markup(markup)

    def set_show_close_button(self, visible):
        """Wether the close button should be visible or not."""
        if visible:
            self.btn_close.show()
        else:
            self.btn_close.hide()



class TabLabel(TabLabelDefault):

    def __init__(self, editor):
        TabLabelDefault.__init__(self, editor.app, editor)
        self.editor = editor
        self.set_close_callback(lambda tl: tl.pane_item.close())
        from cf.ui.editor import Editor
        if isinstance(editor, Editor):
            self.editor.connect("connection-changed",
                                self.on_editor_connection_changed)
            buffer = self.editor.textview.get_buffer()
            buffer.connect("changed", self.on_buffer_changed)
            self.update_label(buffer)
        self.update_tooltip()
        self.show_all()

    def on_buffer_changed(self, buffer):
        gobject.idle_add(self.update_label, buffer)

    def on_close_editor(self, *args):
        self.editor.close()

    def on_editor_connection_changed(self, editor, connection):
        self.update_tooltip()

    def on_show_in_separate_window(self, item):
        gobject.idle_add(self.editor.show_in_separate_window)

    def update_label(self, buffer):
        if self.editor.get_filename():
            fname = self.editor.get_filename()
            txt = os.path.split(fname)[-1]
            self.label.set_tooltip_text(fname)
            if self.editor.file_contents_changed():
                txt = "*"+txt
        else:
            self.label.set_tooltip_text("")
            txt = buffer.get_text(*buffer.get_bounds())
            txt = re.sub("\s+", " ", txt)
        txt = txt.strip()
        if not txt:
            txt = _(u"Query")
        self.set_text(txt)
        self.update_tooltip()

    def update_tooltip(self):
        from cf.ui.editor import Editor
        if isinstance(self.editor, Editor):
            markup = "<b>Connection:</b> "
            if self.editor.connection:
                markup += self.editor.connection.get_label()
            else:
                markup += "["+_(u"Not connected")+"]"
            if self.editor.get_filename():
                markup += "\n<b>File:</b> "+self.editor.get_filename()
            self.set_tootltip(markup)
            conn = self.editor.connection
            if conn:
                self.set_datasource(conn.datasource)
            else:
                self.set_datasource(None)

