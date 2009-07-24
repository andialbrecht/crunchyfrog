# -*- coding: utf-8 -*-

# crunchyfrog - a database schema browser and query tool
# Copyright (C) 2009 Andi Albrecht <albrecht.andi@gmail.com>
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

"""Database access."""

import binascii
import logging
import random
import os
import sys
import thread
import time
from ConfigParser import ConfigParser
from gettext import gettext as _
from threading import Thread

import gobject
import gtk

try:
    import gnomekeyring
    USE_KEYRING = True
except ImportError:
    USE_KEYRING = False

import sqlparse


TRANSACTION_IDLE = 1 << 1
TRANSACTION_COMMIT_ENABLED = 1 << 2
TRANSACTION_ROLLBACK_ENABLED = 1 << 3
TRANSACTION_ACTIVE = TRANSACTION_COMMIT_ENABLED|TRANSACTION_ROLLBACK_ENABLED


# See http://www.sqlalchemy.org/docs/05/dbengine.html#supported-dbapis
DIALECTS = {
    'postgres': {
        'name': 'Postgres',
        'description': _(u'Provides access to PostgreSQL databases'),
        'dependencies': ['psycopg2'],
    },
    'sqlite': {
        'name': 'SQLite',
        'description': _(u'Provides access to SQLite databases'),
        'dependencies': [],  # we need sqlite3, but we need Python 2.5 too ;-)
    },
    'mysql': {
        'name': 'MySQL',
        'description': _(u'Provides access to MySQL databases'),
        'dependencies': ['mysqldb'],
    },
    'oracle': {
        'name': 'Oracle',
        'description': _(u'Provides access to Oracle databases'),
        'dependencies': ['cx_Oracle'],
    },
    'mssql': {
        'name': 'SQL Server',
        'description': _(u'Provides access to SQL Server databases'),
        'dependencies': ['pyodbc pymssql adodbapi'],  # alternatives
    },
#    'access': {
#        'name': 'MS Access',
#        'description': _(u'Provides access to MS Access files'),
#        'dependencies': ['win32com', 'pythoncom', 'pyodbc'],
#   },
    'firebird': {
        'name': 'Firebird',
        'description': _(u'Provides access to Firebird databses'),
        'dependencies': ['kinterbasdb'],
    },
    'informix': {
        'name': 'Informix',
        'description': _(u'Provides access to Informix databases'),
        'dependencies': ['informixdb'],
    },
    'maxdb': {
        'name': 'MaxDB',
        'description': _(u'Provides access to MaxDB databases'),
        'dependencies': ['sapdb'],
    },
}


import cf
from cf.db import backends
from cf.db.meta import DatabaseMeta
from cf.db.url import make_url
from cf.ui import dialogs
from cf.utils import Emit


def availability():
    """Checks for availability of backends.

    Returns a dictionary with backend names as keys. The values are 2-tuples
    (available, reason) where *available* is a flag indicating if the
    backend is available on this system and *reason* is a message why a
    backend isn't available or ``None`` if the backend is available.
    """
    result = {}
    for name in DIALECTS:
        backend = get_dialect_backend(name)
        try:
            api = backend.dbapi()
            result[name] = (True, None)
        except ImportError, err:
            logging.debug('Dialect not available: %s', err)
            result[name] = (False, u'%s' % err)
    return result


def get_dialect_backend(dialect):
    """Return backend class for dialect."""
    modname = 'cf.db.backends.%s' % dialect
    mod = __import__(modname, fromlist=modname.split('.'))
    return mod.DRIVER


class Datasource(gobject.GObject):

    __gsignals__ = {
        'executed': (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT,)),
        }

    def __init__(self, manager):
        self.__gobject_init__()
        self._engine = None
        self.connections = set()
        self.manager = manager
        self.internal_connection = None
        self._meta = None
        self._conn_count = 0
        self._url = None
        self._backend = None
        self.ask_for_password = False
        self.startup_commands = None
        self.name = None
        self.description = None
        self.color = None
        self.id = None

    @property
    def meta(self):
        if self._meta is None:
            if not self.connections:
                return None
            self._meta = DatabaseMeta(self)
        return self._meta

    @property
    def backend(self):
        return self._backend

    def _get_url(self):
        return self._url

    def _set_url(self, url):
        old_url = self._url
        self._url = url
        if ((old_url is not None
             and old_url.drivername != self._url.drivername)
            or old_url is None):
            self._backend = get_dialect_backend(self._url.drivername)()

    url = property(fget=_get_url, fset=_set_url)

    @property
    def public_url(self):
        """URL without password."""
        pwd = self.url.password
        if pwd is not None:
            self.url.password = 'XXX'
        ret = str(self.url)
        if pwd is not None:
            self.url.password = pwd
        return ret

    def _open_connection(self):
        """Internal method to create a Connection instance.

        This method is used for the 'Test Connection' feature.
        """
        if self.ask_for_password and self.url.password is None:
            msg = 'Please enter the password to connect to %(name)s.'
            msg = msg % {'name': self.name or str(self.url)}
            pwd = dialogs.password(_(u'Password required'), msg)
            self.url.password = pwd  # remember while this instance lives
        conn = self.backend.get_connection(self.url)
        conn = Connection(self, conn)
        self.backend.prepare_connection(conn)
        if self.startup_commands:
            conn.execute(self.startup_commands)
        return conn

    def on_connection_closed(self, connection):
        if connection in self.connections:
            self.connections.remove(connection)
        if connection == self.internal_connection:
            self.internal_connection = None
            for conn in self.connections:
                self.internal_connection = conn
                break
        self.manager.emit('datasource-changed', self)

    def dbconnect(self):
        """Returns a database connection."""
        try:
            conn = self._open_connection()
            self._conn_count += 1
            conn.num = self._conn_count
            self.connections.add(conn)
            conn.connect('closed', self.on_connection_closed)
            if self.internal_connection is None:
                self.internal_connection = conn
            if self.manager is not None:
                self.manager.emit('datasource-changed', self)
            return conn
        except:
            logging.exception('Datasource.dbconnect failed:')
            msg = _(u'Could not connect to %(name)s: %(error)s')
            msg = msg % {'name': self.get_label(),
                         'error': str(sys.exc_info()[1])}
            dialogs.error(_(u'Failed'), msg)
            return None

    def dbdisconnect_all(self):
        """Disconnect all open connections."""
        while self.connections:
            conn = self.connections.pop()
            conn.close()

    def get_connections(self):
        return self.connections

    def get_label(self):
        if self.name:
            return '%s (%s)' % (self.name, self.public_url)
        return self.public_url

    def to_dict(self):
        data = {}
        data['ask_for_password'] = self.ask_for_password
        data['name'] = self.name
        data['description'] = self.description
        data['color'] = self.color
        data['id'] = self.id
        data['url'] = self.url
        for key in ('username', 'password', 'host', 'port', 'database'):
            data[key] = getattr(self.url, key)
        data.update(self.url.query)
        return data


class Connection(gobject.GObject):

    __gsignals__ = {
        'closed': (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            tuple()),
        'notice' : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (str,)),
    }

    __gproperties__ = {
        'transaction-state': (
            gobject.TYPE_PYOBJECT,
            'Transaction flag', 'Transaction flag',
            gobject.PARAM_READWRITE),
    }

    def __init__(self, datasource, real_conn):
        self._transaction_state = TRANSACTION_IDLE
        self.__gobject_init__()
        self.datasource = datasource
        self.connection = real_conn
        self.num = 0

    @property
    def threadsafety(self):
        # Workaround to simulate some DB-API2 stuff
        if self.datasource.url.drivername != 'sqlite':
            return 2
        return 1

    @property
    def meta(self):
        return self.datasource.meta

    def do_set_property(self, property, value):
        if property.name == "transaction-state":
            self._transaction_state = value
        else:
            raise AttributeError, "unknown property %r" % property.name

    def do_get_property(self, property):
        if property.name == "transaction-state":
            return self._transaction_state
        else:
            raise AttributeError, "unknown property %r" % property.name

    def get_label(self, short=False):
        """Return a label for this connection.

        :param short: If ``True``, data source information will be omitted.
          Defaults to ``False``.
        """
        if short:
            return _(u'Connection #%(num)d') % {'num': self.num}
        else:
            return '%s #%d' % (self.datasource.get_label(), self.num)

    def execute(self, sql):
        cur = self.connection.cursor()
        cur.execute(sql)
        if cur.description:
            return cur.fetchall()

    def get_dbapi_connection(self):
        return self.connection

    def close(self):
        self.connection.close()
        self.emit('closed')

    def prepare_statement(self, sql):
        """Prepare sql before executing."""
        return self.datasource.backend.prepare_statement(sql)

    def execute_raw(self, sql):
        """Just for internal use!."""
        conn = self.connection
        cur = conn.cursor()
        cur.execute(sql)
        description = cur.description
        ret = []
        if description:
            for row in cur.fetchall():
                data = {}
                for idx, item in enumerate(description):
                    data[item[0]] = row[idx]
                    data[idx] = row[idx]
                ret.append(data)
            return ret

    def begin(self):
        """Start transaction."""
        # We don't support nested transactions.
        if not self.datasource.backend.begin(self):
            self.connection.begin()
        self.update_transaction_state()

    def commit(self):
        """Commit changes."""
        if not self.datasource.backend.commit(self):
            self.connection.commit()
        self.update_transaction_state()

    def rollback(self):
        """Rollback changes."""
        if not self.datasource.backend.rollback(self):
            self.connection.rollback()
        self.update_transaction_state()

    def update_transaction_state(self):
        """Update the current transaction state."""
        old_state = self.get_property('transaction-state')
        new_state = self.datasource.backend.get_transaction_state(self)
        if new_state is None:
            if self.connection.in_transaction:
                new_state = TRANSACTION_COMMIT_ENABLED | \
                            TRANSACTION_ROLLBACK_ENABLED
            else:
                new_state = TRANSACTION_IDLE
        if new_state != old_state:
            self.set_property('transaction-state', new_state)

    def explain_statements(self, statement):
        """Return a list of statements to execute for EXPLAIN."""
        explain = self.datasource.backend.get_explain_statement(statement)
        if explain is None:
            return []
        if not isinstance(explain, (list, tuple)):
            explain = [explain]
        return explain


class DatasourceManager(gobject.GObject):

    __gsignals__ = {
        'datasource-changed': (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT,)),
        'datasource-added': (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT,)),
        'datasource-deleted': (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, app):
        self.app = app
        self._cache = {}
        self.__gobject_init__()

    def _get_config(self):
        conf = ConfigParser()
        fname = os.path.join(cf.USER_CONFIG_DIR, 'datasources.cfg')
        if os.path.exists(fname):
            conf.readfp(open(fname))
        return conf

    def _get_id(self):
        key = ''.join(map(chr, (random.randrange(256) for i in xrange(16))))
        return binascii.hexlify(key)

    def save(self, datasource):
        """Save data source."""
        if datasource.id is None:
            datasource.id = self._get_id()
            sig_name = 'datasource-added'
        else:
            sig_name = 'datasource-changed'
        conf = self._get_config()
        if conf.has_section(datasource.id):
            conf.remove_section(datasource.id)
        conf.add_section(datasource.id)
        pwd = None
        if (datasource.url.password and datasource.ask_for_password
            or USE_KEYRING):
            if USE_KEYRING:
                self.store_password(datasource)
            pwd = datasource.url.password
            datasource.url.password = None
        conf.set(datasource.id, 'url', datasource.url)
        conf.set(datasource.id, 'ask_for_password',
                 datasource.ask_for_password)
        conf.set(datasource.id, 'startup_commands',
                 datasource.startup_commands or '')
        conf.set(datasource.id, 'name', datasource.name or '')
        conf.set(datasource.id, 'description', datasource.description or '')
        conf.set(datasource.id, 'color', datasource.color or '')
        fp = open(os.path.join(cf.USER_CONFIG_DIR, 'datasources.cfg'), 'w')
        conf.write(fp)
        fp.close()
        if pwd is not None:
            datasource.url.password = pwd
        self._cache[datasource.id] = datasource
        self.emit(sig_name, datasource)

    def load(self, id_, conf=None):
        """Load data source with given ID."""
        if id_ in self._cache:
            return self._cache[id_]
        if conf is None:
            conf = self._get_config()
        if not conf.has_section(id_):
            raise RuntimeError('Unknown data source %s' % id_)
        ds = Datasource(manager=self)
        ds.id = id_
        ds.url = make_url(conf.get(id_, 'url'))
        self.get_password_from_keyring(ds)
        ds.ask_for_password = conf.getboolean(id_, 'ask_for_password')
        ds.startup_commands = conf.get(id_, 'startup_commands') or None
        ds.name = conf.get(id_, 'name') or None
        ds.description = conf.get(id_, 'description') or None
        ds.color = conf.get(id_, 'color') or None
        self._cache[id_] = ds
        return ds

    def delete(self, datasource):
        """Delete a data source."""
        conf = self._get_config()
        if conf.has_section(datasource.id):
            conf.remove_section(datasource.id)
        fp = open(os.path.join(cf.USER_CONFIG_DIR, 'datasources.cfg'), 'w')
        conf.write(fp)
        fp.close()
        if USE_KEYRING:
            datasource.password = None
            self.store_password(datasource)
        self.emit('datasource-deleted', datasource)

    def get_all(self):
        """Return all datasources."""
        conf = self._get_config()
        res = []
        for id_ in conf.sections():
            res.append(self.load(id_, conf))
        return res

    def get_connections(self):
        """Return a list of open connections."""
        res = []
        for datasource in self.get_all():
            res += datasource.get_connections()
        return res

    def store_password(self, datasource):
        """Update password.

        If the gnomekeyring bindings are available, the password is stored
        in the keyring. Otherwise it's stored in datasources.cfg.

        It's assumed, that the data source has an ID. So, this method
        *must* be called after the data source has been saved once.

        :param datasource: A data source.
        """
        if not USE_KEYRING:
            return

        item_type = gnomekeyring.ITEM_GENERIC_SECRET
        attrs = {"crunchyfrog": datasource.id}
        try:
            entry = gnomekeyring.find_items_sync(item_type, attrs)
            entry = entry[0]
        except gnomekeyring.NoMatchError:
            entry = None
        if datasource.url.password is not None:
            gnomekeyring.item_create_sync(None, item_type,
                                          'crunchyfrog/%s' % datasource.id,
                                          attrs, datasource.url.password, True)
        elif entry is not None:
            gnomekeyring.item_delete_sync(None, entry.item_id)

    def get_password_from_keyring(self, datasource):
        """Retrieve password from keyring and set it to datasource."""
        if not USE_KEYRING or datasource.url.password:
            return
        item_type = gnomekeyring.ITEM_GENERIC_SECRET
        attrs = {"crunchyfrog": datasource.id}
        try:
            entry = gnomekeyring.find_items_sync(item_type, attrs)
            entry = entry[0]
        except gnomekeyring.NoMatchError:
            entry = None
        if entry is not None:
            datasource.url.password = entry.secret


class Query(gobject.GObject):
    """Object representing a database query."""

    __gsignals__ = {
        "started" : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     tuple()),
        "finished" : (gobject.SIGNAL_RUN_LAST,
                      gobject.TYPE_NONE,
                      tuple())
    }

    def __init__(self, statement, connection):
        """Constructor.

        :param statement: Raw SQL statement.
        :param connection: A database connection.
        """
        self.__gobject_init__()
        self.connection = connection
        self.statement = self.connection.prepare_statement(statement)
        self._parsed = None
        self.description = None
        self.rowcount = -1
        self.rows = None
        self.messages = []
        self.failed = False
        self.executed = False
        self.execution_time = None
        self.coding_hint = "utf-8"
        self.errors = list()

    @property
    def parsed(self):
        if self._parsed is None:
            self._parsed = sqlparse.parse(self.statement)[0]
        return self._parsed

    def execute(self, threaded=False):
        """Execute the statement.

        :param threaded: If ``True`` the statement is executed in threaded
          mode, otherwise in blocking mode (default: ``False``).
        """
        if threaded:
            Emit(self, "started")
        else:
            self.emit("started")
        start = time.time()
        dbapi_conn = self.connection.get_dbapi_connection()
        dbapi_cur = dbapi_conn.cursor()
        try:
            dbapi_cur.execute(self.statement)
        except:
            self.failed = True
            self.errors.append(str(sys.exc_info()[1]))
        self.executed = True
        self.execution_time = time.time() - start
        if not self.failed:
            if hasattr(dbapi_cur, 'statusmessage'):
                self.messages = [dbapi_cur.statusmessage]
            else:
                self.messages = []
            self.description = dbapi_cur.description
            self.rowcount = dbapi_cur.rowcount
            if self.description:
                self.rows = dbapi_cur.fetchall()
        self.connection.update_transaction_state()
        if threaded:
            Emit(self, "finished")
            Emit(self.connection.datasource, 'executed', self)
        else:
            self.emit("finished")
            self.connection.datasource.emit('executed', self)
