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

from gettext import gettext as _

import gtk


class PaneItem(object):
    name = None
    icon = None
    detachable = False

    def get_pane_id(self):
        raise NotImplementedError

    def get_pane_icon(self):
        return gtk.STOCK_MISSING_IMAGE

    def get_pane_name(self):
        return '???'

    def get_pane_detachable(self):
        return False


class Pane(object):
    """Base class for all pane widgets."""

    def __init__(self, mainwin):
        self.app = mainwin.app
        self.mainwin = mainwin
        self._merge_ui()
        hbox = gtk.HBox()
        hbox.set_spacing(5)
        hbox.set_border_width(7)
        self.top_img = gtk.Image()
        hbox.pack_start(self.top_img, False, False)
        self.top_img.show()
        self.top_label = gtk.Label()
        self.top_label.set_alignment(0, 0.5)
        hbox.pack_start(self.top_label)
        self.top_label.show()
        self.top_btn = gtk.Button()
        self.top_btn.add(gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_NONE))
        self.top_btn.set_relief(gtk.RELIEF_NONE)
        self.top_btn.connect('button-press-event', self.on_top_btn_clicked)
        hbox.pack_start(self.top_btn, False, False)
        self.top_btn.show_all()
        self.pack_start(hbox, False, False)
        hbox.show()
        self.notebook = gtk.Notebook()
        self.notebook.set_tab_pos(gtk.POS_BOTTOM)
        self.pack_start(self.notebook, True, True)
        self.notebook.show()
        self.notebook.connect('switch-page', self.on_notebook_switch_page)
        self.notebook.connect('page-added',
                              self.on_notebook_pages_changed, 'added')
        self.notebook.connect('page-removed',
                              self.on_notebook_pages_changed, 'removed')
        self.hide()
        self._state_restored = False
#        self.on_notebook_pages_changed(self.notebook, None, 0, 'removed')

    def _merge_ui(self):
        ui = self.mainwin.ui
        for group in ui.get_action_groups():
            if group.get_name() == 'instance':
                group.add_toggle_actions(self.get_action_entries())
        self.mainwin.ui.add_ui_from_string(self.get_ui_description())
        self.mainwin.ui.ensure_update()

    def _restore(self):
        action_name = 'instance-toggle-%s' % self.__class__.__name__.lower()
        conf_name = 'win.%s_visible' % self.__class__.__name__.lower()
        action = self.mainwin._get_action(action_name)
        action.set_active(self.app.config.get(conf_name, True))
        self.on_toggle(action)

    def on_notebook_pages_changed(self, nb, page, page_num, action_str):
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
            visopt = 'win.%s_visible' % self.__class__.__name__
            if not action.get_active() and action_str == 'added' \
                   and page_num == 0 and self.app.config.get(visopt, False):
                action.set_active(True)

    def on_notebook_switch_page(self, nb, unusable, page_num):
        page = nb.get_nth_page(page_num)
        self.top_label.set_text(page.name)
        it = gtk.icon_theme_get_default()
        pb = it.load_icon(page.icon, gtk.ICON_SIZE_MENU,
                          gtk.ICON_LOOKUP_FORCE_SVG)
        self.top_img.set_from_pixbuf(pb)

    def on_page_detach(self, menuitem, page):
        def attach(window, page):
            page.reparent(self.notebook)
        w = gtk.Window()
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
        self.app.config.set('win.%s_visible' % self.__class__.__name__.lower(),
                            toggle_action.get_active())

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
        menu.popup(None, None, None, event.button, event.time)

    def get_action_entries(self):
        raise NotImplementedError

    def get_ui_description(self):
        return self.UI_DESCRIPTION

    def add_item(self, item):
        """Add a PaneItem."""
        assert isinstance(item, PaneItem)
        it = gtk.icon_theme_get_default()
        pb = it.load_icon(item.icon, gtk.ICON_SIZE_MENU,
                          gtk.ICON_LOOKUP_FORCE_SVG)
        img = gtk.image_new_from_pixbuf(pb)
        img.set_tooltip_text(item.name)
        img.show()
        item.show()
        self.notebook.append_page(item, img)

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

    def set_hidden(self, hidden):
        """Hide/show the pane."""
        raise NotImplementedError

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

    def get_action_entries(self):
        return (
            ('instance-toggle-bottompane', None,
             _(u'_Bottom Pane'), '<control>F9',
             _(u'Show or hide the bottom pane in the current window'),
             self.on_toggle),
        )
