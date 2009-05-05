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

"""SQL Server backend."""

from cf.db import objects
from cf.db.backends import Generic, DEFAULT_OPTIONS


class MSSql(Generic):

    drivername = 'mssql'

    @classmethod
    def dbapi(cls):
        import pymssql
        return pymssql

    @classmethod
    def get_connect_params(cls, url):
        opts = url.get_dict()
        if 'username' in opts:
            opts['user'] = opts['username']
            del opts['username']
        return tuple(), opts

    @classmethod
    def get_options(cls):
        return DEFAULT_OPTIONS

    def get_server_info(self, connection):
        ver = connection.execute('SELECT @@VERSION')[0][0]
        ver = ver.splitlines()[0].strip()+" - "+ver.splitlines()[-1].strip()
        return ver

    def _query(self, connection, sql):
        return connection.execute_raw(sql)

    def initialize(self, meta, connection):
        schemata = objects.Schemata(meta)
        meta.set_object(schemata)
        for item in self._query(connection, INITIAL_SQL):
            schema = meta.find_exact(cls=objects.Schema,
                                     name=item['table_catalog'])
            if schema is None:
                schema = objects.Schema(meta, name=item['table_catalog'],
                                        parent=schemata)
                meta.set_object(schema)
            if item['table_type'] == 'BASE TABLE':
                cls = objects.Table
                coll_cls = objects.Tables
            elif item['table_type'] == 'VIEW':
                cls = objects.View
                coll_cls = objects.Views
            else:
                continue
            parent = meta.find_exact(cls=coll_cls, parent=schema)
            if parent is None:
                parent = coll_cls(meta, parent=schema)
                meta.set_object(parent)
            obj = meta.find_exact(cls=cls, name=item['table_name'],
                                  parent=parent)
            if obj is None:
                obj = cls(meta, name=item['table_name'],
                          parent=parent)
                meta.set_object(obj)
            col = meta.find_exact(cls=objects.Column, name=item['column_name'],
                                  parent=obj.columns)
            if col is None:
                col = objects.Column(meta, name=item['column_name'],
                                     parent=obj.columns)
                meta.set_object(col)


DRIVER = MSSql


INITIAL_SQL = """SELECT t.table_catalog,
t.table_name, c.column_name, t.table_type
FROM information_schema.columns c,
    information_schema.tables t
WHERE t.TABLE_NAME = c.TABLE_NAME
      AND t.table_catalog = c.table_catalog
ORDER BY c.table_catalog,
         c.TABLE_NAME,
         c.ordinal_position
"""
