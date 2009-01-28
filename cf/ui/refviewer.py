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

"""Reference Viewer Plugin

Todo
====

 * SEGFAULT when closing an re-opening RefView
"""

import gtk
import gobject

from cf.plugins.core import BottomPanePlugin
from cf.plugins.mixins import InstanceMixin
from cf.ui import GladeWidget
from cf.ui.pane import PaneItem


class ReferenceViewer(BottomPanePlugin, InstanceMixin):

    id = "crunchyfrog.plugin.refbrowser"
    name = _(u"Reference Browser")
    description = _(u"A tiny webbrowser to view references")
    icon = "stock_help-book"
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://cf.andialbrecht.de"
    version = "0.1"

    def __init__(self, app):
        BottomPanePlugin.__init__(self, app)
        self._views = {}

    def init_instance(self, instance):
        view = RefView(instance)
        self._views[instance] = view
        instance.bottom_pane.add_item(view)

    def deactivate_instance(self, instance):
        if instance in self._views:
            self._views[instance].destroy()
            del self._views[instance]

    def shutdown(self):
        while self._views:
            instance, view = self._views.popitem()
            view.destroy()


class RefView(GladeWidget, PaneItem):

    name = _(u'References')
    icon = 'stock_help-book'
    detachable = True

    def __init__(self, instance):
        GladeWidget.__init__(self, instance, "crunchyfrog", "reference_viewer")
        self.instance = instance

    def _setup_widget(self):
        import gtkmozembed
        self.browser = gtkmozembed.MozEmbed()
        self.browser.show()
        self.xml.get_widget("refviewer_box_moz").pack_start(self.browser, True, True)
        self.list_bookmarks = self.xml.get_widget("refviewer_bookmarks")
        model = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, str) # backend, url, label
        self.list_bookmarks.set_model(model)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=2)
        self.list_bookmarks.append_column(col)
        from cf.plugins.core import PLUGIN_TYPE_BACKEND
        for be in self.app.plugins.get_plugins(PLUGIN_TYPE_BACKEND, True):
            if be.reference and be.reference.base_url:
                iter = model.append(None)
                model.set(iter, 0, be, 1, be.reference.base_url,
                          2, be.reference.name)

    def on_bookmarks_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        self.load_url(model.get_value(iter, 1))

    def on_load_url(self, *args):
        self.load_url(self.xml.get_widget("refviewer_entry_url").get_text())

    def on_toggle_favorites(self, btn):
        if btn.get_active():
            self.xml.get_widget("refviewer_sw_favorites").show_all()
        else:
            self.xml.get_widget("refviewer_sw_favorites").hide()

    def on_toggle_navigationbar(self, btn):
        if btn.get_active():
            self.xml.get_widget("refviewer_box_navigator").show_all()
        else:
            self.xml.get_widget("refviewer_box_navigator").hide()

    def load_url(self, url):
        self.xml.get_widget("refviewer_entry_url").set_text(url)
        self.browser.load_url(url)
