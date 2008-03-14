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

"""Datasource handling"""

import gobject
import cPickle

import logging
log = logging.getLogger("DS")

class DatasourceInfo(gobject.GObject):
    
    def __init__(self, app, backend, name=None, description=None, options={}):
        """
        The constructor of this class takes up to five arguments:
        
        :Parameter:
            app
                `CFApplication`_ instance
            backend
                Instance of a `DBBackendPlugin`_ plugin
            name
                Datasource name (optional)
            description
                Datasource description (optional)
            options
                Backend specific options (optional)
        
        .. _CFApplication: cf.app.CFApplication.html
        .. _DBBackendPlugin: cf.plugins.core.DBBackendPlugin.html
        """
        self.__gobject_init__()
        self.app = app
        self.db_id = None
        self.backend = backend
        self.name = name
        self.description = description
        self.options = options
        self.has_details = False
        self.__conncount = 1L
        self.__connections = list()
        self.internal_connection = None
        
    def __cmp__(self, other):
        return cmp(self.db_id, other.db_id)
        
    def get_label(self):
        return self.backend.get_label(self)
    
    def save(self):
        cur = self.app.userdb.cursor
        conn = self.app.userdb.conn
        if not self.db_id:
            sql = "insert into datasource (name, description, backend, options) \
            values (?,?,?,?)"
            cur.execute(sql, (self.name, self.description, self.backend.id,
                              self.serialize_options()))
            self.db_id = cur.lastrowid
            conn.commit()
            self.app.datasources.emit("datasource-added", self)
        else:
            sql = "update datasource set name=?, description=?, backend=?, \
            options=? where id=?"
            cur.execute(sql, (self.name, self.description, self.backend.id,
                              self.serialize_options(), self.db_id))
            conn.commit()
            self.app.datasources.emit("datasource-modified", self)
            
    def delete(self):
        cur = self.app.userdb.cursor
        conn = self.app.userdb.conn
        sql = "delete from datasource where id=?"
        cur.execute(sql, (self.db_id,))
        conn.commit()
        self.app.datasources.emit("datasource-deleted", self)
            
    def serialize_options(self):
        return cPickle.dumps(self.options)
    
    def deserialize_options(self, data):
        return cPickle.loads(data)
    
    @classmethod
    def load(cls, app, db_id):
        cur = app.userdb.cursor
        sql = "select name, description, backend, options from datasource \
        where id=?"
        cur.execute(sql, (db_id,))
        res = cur.fetchone()
        backend = app.plugins.by_id(res[2])
        opts = cPickle.loads(str(res[3]))
        i = cls(app, backend, res[0], res[1], opts)
        i.db_id = db_id
        return i
    
    @classmethod
    def load_all(cls, app):
        cur = app.userdb.cursor
        sql = "select id from datasource"
        cur.execute(sql)
        r = list()
        for item in cur.fetchall():
            r.append(cls.load(app, item[0]))
        return r
    
    def get_connections(self):
        return self.__connections
    
    def add_connection(self, connection):
        connection.connect("closed", self.on_connection_closed)
        self.__connections.append(connection)
        self.app.datasources.emit("datasource-modified", self)
        
    def on_connection_closed(self, connection):
        if connection in self.__connections:
            self.__connections.remove(connection)
        if connection == self.internal_connection:
            self.internal_connection = None
        gobject.idle_add(self.app.datasources.emit, "datasource-modified", self)
            
    def dbconnect(self):
        conn = self.backend.dbconnect(self.options)
        conn.datasource_info = self
        conn.conn_number = self.__conncount
        self.__conncount += 1
        if not self.internal_connection:
            self.internal_connection = conn
        self.add_connection(conn)
        return conn
    
    def dbdisconnect(self):
        while self.__connections:
            conn = self.__connections[0]
            log.info("Closing connection %s" % conn)
            conn.close()
    
class DatasourceManager(gobject.GObject):
    """Datasource manager
    
    An instance of this class is accessible through the ``datasources``
    attribute of an `CFApplication`_ instance.
    
    Signals
    =======
        datasource-added
            ``def callback(manager, datasource_info, user_param1, ...)``
            
            Emitted when a datsource was added
            
        datasource-deleted
            ``def callback(manager, datasource_info, user_param1, ...)``
            
            Emitted when a datasource was removed
            
        datasource-modified
            ``def callback(manager, datasource_info, user_param1, ...)``
            
            Emitted when a datasource was modified
            
    .. _CFApplication: cf.app.CFApplication.html
            
    """
    
    __gsignals__ = {
        "datasource-added" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT,)),
        "datasource-deleted" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT,)),
        "datasource-modified" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT,)),
    }
    
    def __init__(self, app):
        """
        The constructor of this class takes one argument:
        
        :Parameter:
            app
                `CFApplication`_ instance
        
        .. _CFApplication: cf.app.CFApplication.html
        """
        self.app = app
        self._cache = list()
        self.__gobject_init__()
        self.connect("datasource-added", self.on_datasource_added)
        self.connect("datasource-deleted", self.on_datasource_deleted)
        self.connect("datasource-modified", self.on_datasource_modified)
        self.app.plugins.connect("plugin-active", self.on_plugin_active)
        for item in DatasourceInfo.load_all(self.app):
            if not item.backend or not self.app.plugins.is_active(item.backend):
                continue
            self._cache.append(item)
        
    def on_datasource_added(self, manager, datasource_info):
        self._cache.append(datasource_info)
    
    def on_datasource_deleted(self, manager, datasource_info):
        if datasource_info in self._cache:
            self._cache.remove(datasource_info)
    
    def on_datasource_modified(self, manager, datasource_info):
        for ds in self._cache:
            if ds != datasource_info:
                continue
            ds.backend = datasource_info.backend
            ds.description = datasource_info.description
            ds.name = datasource_info.name
            ds.options = datasource_info.options
            
    def on_plugin_active(self, manager, plugin, active):
        if not plugin._entry_point_group == "crunchyfrog.backend":
            return
        for item in DatasourceInfo.load_all(self.app):
            if item.backend and active and item not in self._cache:
                self.emit("datasource-added", item)
            elif not active and item in self._cache:
                item.dbdisconnect()
                self.emit("datasource-deleted", item)
        
    def get_all(self):
        """Returns all datasources
        
        :Returns: List of `DatasourceInfo`_ instances
        
        .. _DatasourceInfo: cf.datasources.DatasourceInfo.html
        """
        return self._cache
        
    
def check_userdb(userdb):
    if not userdb.get_table_version("datasource"):
        sql = "create table datasource (id integer primary key, \
        name text, description text, backend text, options text, \
        last_accessed real, num_accessed integer)"
        userdb.create_table("datasource", "0.1", sql)