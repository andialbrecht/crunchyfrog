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

"""LDAP Backend (experimental)"""

import gtk
import gobject

import sys

from cf.backends import DBConnection, DBConnectError
from cf.backends.schema import SchemaProvider, Node
from cf.plugins.core import DBBackendPlugin
from cf.datasources import DatasourceInfo
from cf.ui.pdock import DockItem

from gettext import gettext as _

import ldap

import logging
log = logging.getLogger("LDAP")

class LDAPBackend(DBBackendPlugin):
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
        
    def init_instance(self, instance):
        instance.browser.connect("object-menu-popup", self.on_object_menu_popup, instance)
        
    def on_object_menu_popup(self, browser, popup, object, instance):
        if isinstance(object, LDAPNode):
            item = gtk.MenuItem(_(u"Details"))
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
            return err.message
        return None
    
class LDAPConnection(DBConnection):
    
    def __init__(self, provider, app, conn, opts):
        DBConnection.__init__(self, provider, app)
        self.conn = conn
        self.opts = opts
        
class LDAPView(gtk.ScrolledWindow):
    
    def __init__(self, data):
        gtk.ScrolledWindow.__init__(self)
        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.model = gtk.ListStore(str, str)
        self.list = gtk.TreeView(self.model)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=0)
        self.list.append_column(col)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=1)
        self.list.append_column(col)
        for key, value in data.items():
            for i in range(len(value)):
                if i == 0:
                    self.model.append([key, value[i]])
                else:
                    self.model.append(["", value[i]])
        self.add(self.list)
        self.list.set_headers_visible(False)
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
        for item in  [x[0] for x in connection.conn.search_st(dn, ldap.SCOPE_ONELEVEL, attrsonly=1)]:
            ret.append(LDAPNode(item.split(",", 1)[0], dn=item, connection=connection))
        return ret
        