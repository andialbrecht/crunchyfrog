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

from cf.plugins.core import GenericPlugin
from cf.ui import GladeWidget
from cf.ui.pdock import DockItem

from gettext import gettext as _

class ReferenceViewer(GenericPlugin):
    id = "crunchyfrog.plugin.refbrowser"
    name = _(u"Reference Browser")
    description = _(u"A tiny webbrowser to view references")
    icon = "stock_help-book"
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://cf.andialbrecht.de"
    version = "0.1"
    
    def __init__(self, app):
        GenericPlugin.__init__(self, app)
        self._viewer = dict()
        self.app.cb.connect("instance-created", self.on_instance_created)
        for instance in app.get_instances():
            self.init_instance(instance)
            
    def on_instance_created(self, app, instance):
        self.init_instance(instance)
        
    def on_toggle_viewer(self, menuitem, instance):
        if menuitem.get_active():
            gobject.idle_add(self.create_view, menuitem, instance)
        else:
            gobject.idle_add(self.remove_view, instance)
            
    def on_view_destroyed(self, view, menuitem, instance):
        menuitem.set_active(False)
        
    def create_view(self, menuitem, instance):
        view = RefView(self.app, instance)
        self._viewer[instance] = view
        item = DockItem(instance.dock, "refview", view.widget, _(u"Reference"), 
                          self.icon, gtk.POS_BOTTOM)
        instance.dock.add_item(item)
        instance.set_data("refviewer", view)
        view.widget.connect("destroy", self.on_view_destroyed, menuitem, instance)
        
    def init_instance(self, instance):
        mn_view = instance.xml.get_widget("mn_view")
        item = gtk.CheckMenuItem(_(u"Reference Viewer"))
        item.connect("activate", self.on_toggle_viewer, instance)
        item.show()
        if self.app.config.get("refviewer.visible"):
            item.set_active(True)
        mn_view.append(item)
        
    def remove_view(self, instance):
        view = self._viewer.pop(instance)
        instance.set_data("refviewer", None)
        view.destroy()
        
    def shutdown(self):
        if self._viewer.keys():
            self.app.config.set("refviewer.visible", True)
        else:
            self.app.config.set("refviewer.visible", False)
            
class RefView(GladeWidget):
    
    def __init__(self, app, instance):
        GladeWidget.__init__(self, app, "crunchyfrog", "reference_viewer")
        self.instance = instance
        
    def _setup_widget(self):
        import gtkmozembed
        self.browser = gtkmozembed.MozEmbed()
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
        