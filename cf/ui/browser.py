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

"""Object browser"""

import gtk
import gobject

from kiwi.ui import dialogs

from cf.datasources import DatasourceInfo
from cf.backends import DBConnectError

from gettext import gettext as _

class DummyNode(object):
    pass

class Browser(gtk.ScrolledWindow):
    
    __gsignals__ = {
        "object-menu-popup" : (gobject.SIGNAL_RUN_LAST,
                               gobject.TYPE_NONE,
                               (gobject.TYPE_PYOBJECT,
                                gobject.TYPE_PYOBJECT)),
    }
    
    def __init__(self, app, instance):
        self.app = app
        self.instance = instance
        self._setup_widget()
        self._setup_connections()
        self.reset_tree()
        
    def _setup_widget(self):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_size_request(250, -1)
        # Model
        self.model = gtk.TreeStore(gobject.TYPE_PYOBJECT, # 0 Object
                                   str, # 1 label
                                   gtk.gdk.Pixbuf, # 2 icon
                                   gobject.TYPE_PYOBJECT, # 3 double-click callback
                                   gobject.TYPE_PYOBJECT, # 4 popup menu callback
                                   str, # 5 tooltip
                                   )
        self.model.set_sort_column_id(1, gtk.SORT_ASCENDING)
        # TreeView
        self.object_tree = gtk.TreeView(self.model)
        self.add(self.object_tree)
        self.object_tree.set_tooltip_column(5)
        col = gtk.TreeViewColumn()
        renderer = gtk.CellRendererPixbuf()
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, 'pixbuf', 2)
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'text', 1)
        self.object_tree.append_column(col)
        self.object_tree.set_headers_visible(False)
        self.object_tree.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, (("text/plain", gtk.TARGET_SAME_APP, 80),), gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY)
        def drag_data_get(treeview, context, selection, info, timestamp):
            treeselection = treeview.get_selection()
            model, iter = treeselection.get_selected()
            text = id(model.get_value(iter, 0))
            selection.set('text/plain', 8, str(text))
            return
        self.object_tree.connect("drag_data_get", drag_data_get)
        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        
    def _setup_connections(self):
        self.app.datasources.connect("datasource-added", self.on_datasource_added)
        self.app.datasources.connect("datasource-deleted", self.on_datasource_deleted)
        self.app.datasources.connect("datasource-modified", self.on_datasource_modified)
        self.object_tree.connect("button-press-event", self.on_button_press_event)
        self.object_tree.connect("row-expanded", self.on_row_expanded)
        sel = self.object_tree.get_selection()
        sel.connect("changed", self.on_object_tree_selection_changed)
        
    def _create_dsinfo_menu(self, model, iter, popup):
        def connect(item, datasource_info):
            try:
                datasource_info.dbconnect()
                self.on_object_tree_selection_changed(self.object_tree.get_selection())
            except DBConnectError, err:
                dialogs.error(_(u"Connection failed"), err.message)
        def disconnect(item, datasource_info):
            datasource_info.dbdisconnect()
            iter = self.get_iter_for_datasource(datasource_info)
            model = self.object_tree.get_model()
            self.object_tree.collapse_row(model.get_path(iter))
        datasource_info = model.get_value(iter, 0)
        if datasource_info.get_connections():
            lbl = _(u"Disconnect")
            cb = disconnect
        else:
            lbl = _(u"Connect")
            cb = connect
        item = gtk.MenuItem(lbl)
        item.connect("activate", cb, datasource_info)
        popup.append(item)
        return popup
        
    def on_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                popup = gtk.Menu()
                model = treeview.get_model()
                iter = model.get_iter(path)
                cb = model.get_value(iter, 4)
                if cb:
                    try:
                        popup = cb(model, iter, popup)
                    except:
                        import traceback; traceback.print_exc()
                self.emit("object-menu-popup", popup, model.get_value(iter, 0))
                if popup.get_children():
                    popup.show_all()
                    popup.popup( None, None, None, event.button, time)
            return 1
        
    def on_datasource_added(self, manager, datasource_info):
        iter = self.model.append(None)
        self.set_datasource_info(iter, datasource_info)
    
    def on_datasource_deleted(self, manager, datasource_info):
        iter = self.get_iter_for_datasource(datasource_info)
        if not iter:
            return
        self.model.remove(iter)
    
    def on_datasource_modified(self, manager, datasource_info):
        iter = self.get_iter_for_datasource(datasource_info)
        if not iter:
            return
        self.set_datasource_info(iter, datasource_info)
        
    def on_object_tree_selection_changed(self, selection):
        model, iter = selection.get_selected()
        if not iter: return
        obj = model.get_value(iter, 0)
        if isinstance(obj, DatasourceInfo):
            if obj.internal_connection:
                server_info = obj.internal_connection.get_server_info()
                if server_info:
                    self.instance.statusbar.set_message(server_info)
                else:
                    self.instance.statusbar.set_message("")
            else:
                self.instance.statusbar.set_message("")
        else:
            comm = model.get_value(iter, 5) or ""
            self.instance.statusbar.set_message(comm)
            
        
    def on_row_expanded(self, treeview, iter, path):
        model = treeview.get_model()
        obj = model.get_value(iter, 0)
        citer = model.iter_children(iter)
        if citer:
            cobj = model.get_value(citer, 0)
            if isinstance(cobj, DummyNode):
                datasource_info = self.find_datasource_info(model, citer)
                model.remove(citer)
                if datasource_info.backend.schema:
                    for child in datasource_info.backend.schema.fetch_children(datasource_info.internal_connection, obj) or []:
                        citer = model.append(iter)
                        if child.icon:
                            icon = gtk.icon_theme_get_default().load_icon(child.icon, gtk.ICON_SIZE_MENU, gtk.ICON_LOOKUP_FORCE_SVG)
                        else:
                            icon = None
                        model.set(citer, 
                                  0, child,
                                  1, child.name,
                                  2, icon,
                                  5, child.description)
                        if child.has_children:
                            cciter = model.append(citer)
                            model.set(cciter, 0, DummyNode())
                    citer = model.iter_children(iter)
                    if citer:
                        treeview.expand_row(model.get_path(iter), False)
                    
    def find_datasource_info(self, model, iter):
        while iter:
            obj = model.get_value(iter, 0)
            if isinstance(obj, DatasourceInfo):
                return obj
            iter = model.iter_parent(iter)
    
    def get_iter_for_datasource(self, datasource_info):
        iter = self.model.get_iter_first()
        while iter:
            if self.model.get_value(iter, 0) == datasource_info:
                return iter
            iter = self.model.iter_next(iter)
        return None
    
    def get_object_by_id(self, id_, iter=None, model=None):
        if not iter:
            model = self.object_tree.get_model()
            iter = model.get_iter_first()
        while iter:
            value = model.get_value(iter, 0)
            if id(value) == id_:
                return value
            citer = model.iter_children(iter)
            while citer:
                ret = self.get_object_by_id(id_, citer, model)
                if ret:
                    return ret
                citer = model.iter_next(citer)
            iter = model.iter_next(iter)
    
    def reset_tree(self):
        self.model.clear()
        for datasource_info in self.app.datasources.get_all():
            iter = self.model.append(None)
            self.set_datasource_info(iter, datasource_info)
    
    def set_datasource_info(self, iter, datasource_info):
        if datasource_info.get_connections():
            ico = gtk.icon_theme_get_default().load_icon("stock_connect", gtk.ICON_SIZE_MENU, gtk.ICON_LOOKUP_FORCE_SVG)
        else:
            ico = gtk.icon_theme_get_default().load_icon("stock_disconnect", gtk.ICON_SIZE_MENU, gtk.ICON_LOOKUP_FORCE_SVG)
        self.model.set(iter,
                  0, datasource_info,
                  1, datasource_info.get_label(),
                  2, ico,
                  3, None,
                  4, self._create_dsinfo_menu,
                  5, datasource_info.description)
        citer = self.model.iter_children(iter)
        if datasource_info.get_connections() \
        and not citer:
            citer = self.model.append(iter)
            self.model.set(citer, 0, DummyNode())
        elif not datasource_info.get_connections() \
        and citer:
            self.model.remove(citer)