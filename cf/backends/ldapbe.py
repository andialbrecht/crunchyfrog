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

"""LDAP backend"""

import gtk
import gobject
import pango

import sys

from cf.backends import DBConnection, DBConnectError
from cf.backends.schema import SchemaProvider, Node
from cf.plugins.core import DBBackendPlugin
from cf.datasources import DatasourceInfo
from cf.ui import GladeWidget
from cf.ui.pdock import DockItem
from cf.ui.widgets import DataExportDialog

from gettext import gettext as _


import logging
log = logging.getLogger("LDAP")

class LDAPBackend(DBBackendPlugin):
    id = "crunchyfrog.backend.ldap"
    name = _(u"LDAP Plugin")
    description = _(u"Provides access to LDAP/ActiveDirectory servers")
        
    def __init__(self, app):
        DBBackendPlugin.__init__(self, app)
        log.info("Activating LDAP backend")
        self.schema = LDAPSchema()
        self.app.cb.connect("instance-created", self.on_instance_created)
        for item in self.app.get_instances():
            self.init_instance(item)
            
    def on_instance_created(self, app, instance):
        self.init_instance(instance)
        
    def on_search_dn(self, menuitem, object, instance):
        search = LDAPSearch(self.app, instance, object.get_data("connection"))
        search.set_search_dn(object.get_data("dn"))
        item = DockItem(instance.dock, "search_%s" % object.get_data("dn"),
                        search.widget, 
                        _(u"Search: %(dn)s") % {"dn" : object.get_data("dn")}, 
                       "gtk-find", None)
        instance.dock.add_item(item)
        
    def init_instance(self, instance):
        instance.browser.connect("object-menu-popup", self.on_object_menu_popup, instance)
        
    def on_object_menu_popup(self, browser, popup, object, instance):
        if isinstance(object, LDAPNode):
            item = gtk.ImageMenuItem("gtk-find")
            item.show()
            item.connect("activate", self.on_search_dn, object, instance)
            popup.append(item)
            sep = gtk.SeparatorMenuItem()
            sep.show()
            popup.append(sep)
            item = gtk.MenuItem(_(u"_Details"))
            item.show()
            item.connect("activate", self.on_object_details, object, instance)
            popup.append(item)
            
    def on_object_details(self, menuitem, object, instance):
        res = object.get_data("connection").conn.search_s(object.get_data("dn"), ldap.SCOPE_BASE)
        view = LDAPView(res[0][1])
        item = DockItem(instance.dock, object.get_data("dn"), view, object.get_data("dn"), 
                       "gtk-edit", None)
        instance.dock.add_item(item)

    @classmethod
    def _get_basedn(cls, entry):
        return entry.get_text().strip() or None
        
    def shutdown(self):
        log.info("Shutting down LDAP backend")
    
    @classmethod
    def get_datasource_options_widgets(cls, data_widgets, initial_data=None):
        lbl = gtk.Label(_(u"Base DN:"))
        lbl.set_alignment(0, 0.5)
        entry_basedn = gtk.Entry()
        if initial_data and initial_data.options.get("base_dn"):
            entry_basedn.set_text(initial_data.options.get("base_dn"))
        data_widgets["base_dn"] = (cls._get_basedn, entry_basedn)
        return data_widgets, ["host", "port", lbl, entry_basedn, "user", "password"]
    
    @classmethod
    def get_label(cls, datasource_info):
        return "%s (%s)" % (datasource_info.name, datasource_info.options.get("host"))
    
    def dbconnect(self, data):
        try:
            import ldap
        except ImportError:
            raise DBConnectError(_(u"Python module ldap is not installed."))
        try:
            conn_args = [data.get("host") or "localhost"]
            conn_args.append(data.get("port") or 389)
            real_conn = ldap.open(*conn_args)
        except:
            raise DBConnectError(str(sys.exc_info()[1]))
        if data.get("user"):
            try:
                real_conn.bind_s(data.get("user"), data.get("password"))
            except:
                raise DBConnectError(str(sys.exc_info()[1]))
        return LDAPConnection(self, self.app, real_conn, data)
    
    def test_connection(self, data):
        try:
            conn = self.dbconnect(data)
            conn.close()
        except DBConnectError, err:
            return str(err)
        return None
    
class LDAPConnection(DBConnection):
    
    def __init__(self, provider, app, conn, opts):
        DBConnection.__init__(self, provider, app)
        self.conn = conn
        self.opts = opts
        
    def _reconnect(self):
        data = self.opts
        conn_args = [data.get("host") or "localhost"]
        conn_args.append(data.get("port") or 389)
        real_conn = ldap.open(*conn_args)
        if data.get("user"):
            try:
                real_conn.bind_s(data.get("user"), data.get("password"))
            except:
                raise DBConnectError(str(sys.exc_info()[1]))
        self.conn = real_conn
        
    def search_s(self, *args, **kw):
        try:
            r = self.conn.search_s(*args, **kw)
        except ldap.SERVER_DOWN:
            self._reconnect()
            r = self.conn.search_s(*args, **kw)
        return r
            
        
class LDAPSearch(GladeWidget):
    
    def __init__(self, app, instance, connection):
        GladeWidget.__init__(self, app, "crunchyfrog", "ldap_search")
        self.connection = connection
        self.instance = instance
        
    def _setup_connections(self):
        self.xml.get_widget("ldap_search_results").connect("button-press-event", self.on_button_press_event)
        
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
                item = gtk.MenuItem(_(u"Export"))
                item.connect("activate", self.on_export)
                item.show()
                popup.append(item)
                popup.show_all()
                popup.popup( None, None, None, event.button, time)
            return 1
        
    def on_do_search(self, *args):
        self.search()
        
    def on_export(self, *args):
        gobject.idle_add(self.export_data)
        
    def on_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        dn = model.get_value(iter, 0)
        res = self.connection.conn.search_s(dn, ldap.SCOPE_BASE)
        view = LDAPView(res[0][1])
        item = DockItem(self.instance.dock, dn, view, dn, 
                       "gtk-edit", None)
        self.instance.dock.add_item(item)
        
    def export_data(self):
        data = []
        treeview = self.xml.get_widget("ldap_search_results")
        model = treeview.get_model()
        iter = model.get_iter_first()
        description = []
        first_row = True
        while iter:
            row = []
            for i in range(len(treeview.get_columns())):
                row.append(model.get_value(iter, i))
                if first_row:
                    col = treeview.get_column(i)
                    description.append((col.get_title(), str, None, None, None, None, None))
            data.append(row)
            first_row = False
            iter = model.iter_next(iter)
        selected = None
        statement = ""
        gtk.gdk.threads_enter()
        dlg = DataExportDialog(self.app, self.instance.widget,
                               data, selected, statement,
                               description)
        if dlg.run() == gtk.RESPONSE_OK:
            dlg.hide()
            dlg.export_data()
        dlg.destroy()
        gtk.gdk.threads_leave()
        
    def search(self):
        search_dn = self.xml.get_widget("ldap_search_dn").get_text()
        if self.xml.get_widget("ldap_search_scope_onelevel").get_active():
            scope = ldap.SCOPE_ONELEVEL
        else:
            scope = ldap.SCOPE_SUBTREE
        filterstr = self.xml.get_widget("ldap_search_filter").get_text()
        attrlist = self.xml.get_widget("ldap_search_attributes").get_text().split(",") 
        r = self.connection.search_s(search_dn, scope, filterstr, attrlist)
        treeview = self.xml.get_widget("ldap_search_results")
        while treeview.get_columns():
            treeview.remove_column(treeview.get_column(0))
        model_args = [str]
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        col = gtk.TreeViewColumn("dn", renderer, text=0)
        col.set_sort_column_id(0)
        col.set_resizable(True)
        col.set_min_width(100)
        col.set_reorderable(True)
        treeview.append_column(col)
        for i in range(len(attrlist)):
            attr = attrlist[i]
            model_args.append(str)
            renderer = gtk.CellRendererText()
            renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
            col = gtk.TreeViewColumn(attr, renderer, text=i+1)
            col.set_sort_column_id(i+1)
            col.set_resizable(True)
            col.set_reorderable(True)
            col.set_min_width(50)
            treeview.append_column(col)
        model = gtk.ListStore(*model_args)
        treeview.set_model(model)
        for item in r:
            row = [item[0]]
            attrs = item[1]
            for i in range(len(attrlist)):
                att = attrlist[i].lower()
                att_set = False
                for key, value in attrs.items():
                    if key.lower() == att and not att_set:
                        row.append("\n".join(value))
                        att_set = True
                if not att_set:
                    row.append("N/A") 
            model.append(row)
        
        
    def set_search_dn(self, dn):
        self.xml.get_widget("ldap_search_dn").set_text(dn)
        
class LDAPView(gtk.ScrolledWindow):
    
    def __init__(self, data):
        gtk.ScrolledWindow.__init__(self)
        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.model = gtk.ListStore(str, str, str)
        self.list = gtk.TreeView(self.model)
        col = gtk.TreeViewColumn(_(u"Attribute"), gtk.CellRendererText(), text=0)
        col.set_sort_column_id(2)
        self.list.append_column(col)
        col = gtk.TreeViewColumn(_(u"Value"), gtk.CellRendererText(), text=1)
        col.set_sort_column_id(1)
        self.list.append_column(col)
        for key, value in data.items():
            for i in range(len(value)):
                if i == 0:
                    self.model.append([key, value[i], key])
                else:
                    self.model.append(["", value[i], key])
        self.add(self.list)
        self.list.set_rules_hint(True)
        
class LDAPNode(Node):
    icon = "gtk-open"
        
class LDAPSchema(SchemaProvider):
    
    def fetch_children(self, connection, parent):
        if isinstance(parent, DatasourceInfo):
            dn = connection.opts.get("base_dn")
        else:
            dn = parent.get_data("dn")
        ret = []
        for item in  [x[0] for x in connection.search_s(dn, ldap.SCOPE_ONELEVEL, attrsonly=1)]:
            node = LDAPNode(item.split(",", 1)[0], dn=item, connection=connection)
            if len(connection.search_s(item, ldap.SCOPE_ONELEVEL, attrsonly=1)) == 0:
                node.has_children = False
                node.icon = "gtk-justify-fill"
            ret.append(node)
        return ret


try:
    import ldap
except ImportError:
    LDAPBackend.INIT_ERROR = _(u"Python module ldap required.")