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

import cPickle
import logging

import gobject

try:
    import gnomekeyring
    USE_KEYRING = True
except ImportError:
    USE_KEYRING = False


log = logging.getLogger("DS")


class DatasourceInfo(gobject.GObject):

    def __init__(self, app, backend, name=None, description=None,
                 options={}, db_id=None):
        """Constructor.

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
            db_id
                Databse ID (optional)

        .. _CFApplication: cf.app.CFApplication.html
        .. _DBBackendPlugin: cf.plugins.core.DBBackendPlugin.html
        """
        self.__gobject_init__()
        self.app = app
        self.db_id = db_id
        self.backend = backend
        self.name = name
        self.description = description
        self.options = self._init_options(options)
        self.has_details = False
        self.__conncount = 1L
        self.__connections = list()
        self.internal_connection = None

    def __cmp__(self, other):
        return cmp(self.db_id, other.db_id)

    def _init_options(self, options):
        """Initialize and return options."""
        if self.backend.password_option not in options:
            pwd = self.get_password(self.db_id)
            options[self.backend.password_option] = pwd
        elif self.backend.password_option \
        and self.backend.password_option in options:
            # upgrade from 0.2 -> 0.3: store password in keyring
            gobject.idle_add(self.save, options)
        return options

    def get_label(self):
        return self.backend.get_label(self)

    def save(self, options=None, emit_signal=True):
        cur = self.app.userdb.cursor
        conn = self.app.userdb.conn
        if options is None:
            options = self.options
        if self.backend.password_option \
        and self.backend.password_option in options:
            passwd = options.pop(self.backend.password_option)
        else:
            passwd = None
        if not self.db_id:
            sql = ("insert into datasource (name, description, "
                   "backend, options) values (?,?,?,?)")
            cur.execute(sql, (self.name, self.description, self.backend.id,
                              self.serialize_options(options)))
            self.db_id = cur.lastrowid
            conn.commit()
            signal = "datasource-added"
        else:
            sql = ("update datasource set name=?, description=?, "
                   "backend=?, options=? where id=?")
            cur.execute(sql, (self.name, self.description, self.backend.id,
                              self.serialize_options(options), self.db_id))
            conn.commit()
            signal = "datasource-modified"
        self.store_password(passwd, self.db_id)
        if self.backend.password_option:
            self.options[self.backend.password_option] = passwd
        if emit_signal:
            self.app.datasources.emit(signal, self)

    def delete(self):
        cur = self.app.userdb.cursor
        conn = self.app.userdb.conn
        sql = "delete from datasource where id=?"
        cur.execute(sql, (self.db_id,))
        conn.commit()
        self.store_password(None, self.db_id)
        self.app.datasources.emit("datasource-deleted", self)

    def serialize_options(self, options):
        return cPickle.dumps(options)

    def deserialize_options(self, data):
        return cPickle.loads(data)

    def store_password(self, pwd, db_id):
        """Update password in keyring.

        Args:
          pwd: Password (delete existing if None)
          db_id: Datasource ID
        """
        if USE_KEYRING:
            self._store_password_keyring(pwd, db_id)
        else:
            self._store_password_userdb(pwd, db_id)

    def _store_password_userdb(self, pwd, db_id):
        sql = "update datasource set password = ? where id = ?"
        cur = self.app.userdb.cursor
        conn = self.app.userdb.conn
        cur.execute(sql, (pwd, db_id))
        conn.commit()

    def _store_password_keyring(self, pwd, db_id):
        item_type = gnomekeyring.ITEM_GENERIC_SECRET
        attrs = {"crunchyfrog": db_id}
        try:
            entry = gnomekeyring.find_items_sync(item_type, attrs)
            entry = entry[0]
        except gnomekeyring.NoMatchError:
            entry = None
        if pwd is not None:
            gnomekeyring.item_create_sync(None, item_type,
                                          ("Password for %s"
                                           % self.get_label()),
                                          attrs, pwd, True)
        elif entry is not None:
            gnomekeyring.item_delete_sync(None, entry.item_id)

    def get_password(self, db_id):
        """Get password from keyring.

        Args:
          db_id: Datasource ID

        Returns:
          Password as string or None.
        """
        if USE_KEYRING:
            return self._get_password_keyring(db_id)
        else:
            return self._get_password_userdb(db_id)

    def _get_password_keyring(self, db_id):
        if db_id is None:
            return None
        item_type = gnomekeyring.ITEM_GENERIC_SECRET
        attrs = {"crunchyfrog": db_id}
        try:
            entry = gnomekeyring.find_items_sync(item_type, attrs)
            return entry[0].secret
        except gnomekeyring.NoMatchError:
            return None

    def _get_password_userdb(self, db_id):
        if db_id is None:
            return None
        sql = "select password from datasource where id = ?"
        cur = self.app.userdb.cursor
        cur.execute(sql, (db_id,))
        res = cur.fetchone()
        if res:
            return res[0]
        return None

    @classmethod
    def load(cls, app, db_id):
        cur = app.userdb.cursor
        sql = ("select name, description, backend, options "
               "from datasource where id=?")
        cur.execute(sql, (db_id,))
        res = cur.fetchone()
        logging.debug('Initiating data source %s with backend %s',
                      res[0], res[2])
        backend = app.plugins.by_id(res[2], False)
        opts = cPickle.loads(str(res[3]))
        i = cls(app, backend, res[0], res[1], opts, db_id=db_id)
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
        gobject.idle_add(self.app.datasources.emit,
                         "datasource-modified", self)

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
    attribute of an :class:`~cf.app.CFApplication` instance.

    :Signals:

    datasource-added
      ``def callback(manager, datasource_info, user_param1, ...)``

      Emitted when a datsource was added

    datasource-deleted
      ``def callback(manager, datasource_info, user_param1, ...)``

      Emitted when a datasource was removed

    datasource-modified
      ``def callback(manager, datasource_info, user_param1, ...)``

      Emitted when a datasource was modified
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
            if not item.backend \
            or not self.app.plugins.is_active(item.backend):
                continue
            self._cache.append(item)
        self._check_password_field()

    def _check_password_field(self):
        cur = self.app.userdb.cursor
        conn = self.app.userdb.conn
        sql = 'pragma table_info(datasource)'
        cur.execute(sql)
        if not 'password' in [x[1] for x in cur.fetchall()]:
            sql = 'alter table datasource add password text'
            cur.execute(sql)
            conn.commit()

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
        from cf.plugins.core import PLUGIN_TYPE_BACKEND
        if not plugin.plugin_type == PLUGIN_TYPE_BACKEND:
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

    def get_connections(self):
        """Returns a list of open connections."""
        for dsinfo in self.get_all():
            for conn in dsinfo.get_connections():
                yield conn


def check_userdb(userdb):
    if not userdb.get_table_version("datasource"):
        sql = ("create table datasource (id integer primary key, "
               "name text, description text, backend text, options text, "
               "last_accessed real, num_accessed integer)")
        userdb.create_table("datasource", "0.1", sql)
