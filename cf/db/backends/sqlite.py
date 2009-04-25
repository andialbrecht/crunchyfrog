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

"""SQLite backend"""

import gobject
import functools

from cf.db import TRANSACTION_IDLE, TRANSACTION_ACTIVE
from cf.db import objects
from cf.db.backends import Generic, GUIOption


class SQLite(Generic):

    drivername = 'sqlite'

    @classmethod
    def get_options(cls):
        return (
            GUIOption('database', _(u'File'),
                      widget=GUIOption.WIDGET_FILECHOOSER,
                      required=True),
            )

    @classmethod
    def get_native_shell_command(cls, url):
        return 'sqlite3', (url.database,)

    @classmethod
    def dbapi(cls):
        import sqlite3
        return sqlite3

    def get_connect_params(self, url):
        return (url.database,), {}

    def prepare_connection(self, connection):
        connection.connection.isolation_level = None
        fpart = functools.partial(self._transaction_watcher, connection)
        connection.connection.set_authorizer(fpart)

    def _transaction_watcher(self, connection, action_code, operation, *args):
        sqlite3 = self.dbapi()
        if action_code != sqlite3.SQLITE_TRANSACTION:
            return sqlite3.SQLITE_OK
        if operation.upper() == 'BEGIN':
            gobject.idle_add(connection.set_property,
                             'transaction-state', TRANSACTION_ACTIVE)
        elif operation.upper() in ('ROLLBACK', 'COMMIT'):
            gobject.idle_add(connection.set_property,
                             'transaction-state', TRANSACTION_IDLE)
            fpart = functools.partial(self._transaction_watcher, connection)
            connection.connection.set_authorizer(fpart)
        return sqlite3.SQLITE_OK

    def get_server_info(self, connection):
        return 'SQLite %s' % self.dbapi().sqlite_version

    def initialize(self, meta, connection):
        sql = 'select type, name, tbl_name, sql from sqlite_master'
        tables = objects.Tables(meta)
        meta.set_object(tables)
        views = objects.Views(meta)
        meta.set_object(views)
        for item in connection.execute(sql):
            if item[0] == 'table':
                table = objects.Table(meta, name=item[1], parent=tables,
                                      createstmt=item[3])
                meta.set_object(table)
            elif item[0] == 'view':
                views = objects.View(meta, name=item[1], parent=views,
                                     createstmt=item[3])
                meta.set_object(views)

    def refresh(self, obj, meta, connection):
        if obj.typeid == 'columns':
            self._refresh_columns(obj, meta, connection)

    def _refresh_columns(self, obj, meta, connection):
        table = obj.parent
        known_columns = {}
        [known_columns.setdefault(k.cid, k)
         for k in meta.find(cls=objects.Column, parent=obj)]
        sql = "pragma table_info('%s')" % table.name  # somehow ? doesn't work
        for item in connection.execute(sql):
            # item is: cid, name, type, notnull, dflt_value, pk
            col = known_columns.get(item[0], None)
            if col is None:
                col = objects.Column(meta, parent=obj, cid=item[0])
            col.name = item[1]
            col.type = item[2]
            col.notnull = item[3]
            col.default = item[4]
            col.pk = item[5]
            meta.set_object(col)


DRIVER = SQLite
