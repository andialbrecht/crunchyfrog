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

"""MS-SQL backend"""

from cf.backends import DBConnectError
from cf.backends.dbapi2helper import DbAPI2Connection
from cf.backends.schema import *
from cf.datasources import DatasourceInfo
from cf.plugins.core import DBBackendPlugin

import time

from gettext import gettext as _

import logging
log = logging.getLogger("MS-SQL")


class MsSQLBackend(DBBackendPlugin):
    id = "crunchyfrog.backend.mssql"
    name = _(u"MS-SQL Plugin")
    description = _(u"Provides access to MS-SQL databases")
    
    def __init__(self, app):
        DBBackendPlugin.__init__(self, app)
        log.info("Activating MS-SQL backend")
        self.schema = MsSQLSchema()
        
    def _get_conn_opts_from_opts(self, opts):
        conn_opts = dict()
        if opts["database"]: conn_opts["database"] = opts["database"]
        if opts["host"]: conn_opts["host"] = opts["host"]
        if opts["user"]: conn_opts["user"] = opts["user"]
        if opts["password"]: conn_opts["password"] = opts["password"]
        return conn_opts
        
    def shutdown(self):
        log.info("Shutting down MS-SQL backend")
    
    @classmethod
    def get_datasource_options_widgets(cls, data_widgets, initial_data=None):
        return data_widgets, ["database", "host", "user", "password"]
    
    @classmethod
    def get_label(cls, datasource_info):
        if not datasource_info.options.get("host", None):
            datasource_info.options["host"] = "localhost"
        return DBBackendPlugin.get_label(datasource_info)
    
    def dbconnect(self, data):
        opts = self._get_conn_opts_from_opts(data)
        if data.get("ask_for_password", False):
            pwd = self.password_prompt()
            if not pwd:
                raise DBConnectError(_(u"No password given."))
            opts["password"] = pwd
        try:
            real_conn = pymssql.connect(**opts)
        except StandardError, err:
            raise DBConnectError(str(err))
        conn = MsSQLConnection(self, self.app, real_conn)
        conn.threadsafety = pymssql.threadsafety
        return conn
    
    def test_connection(self, data):
        try:
            conn = self.dbconnect(data)
            conn.close()
        except DBConnectError, err:
            return str(err)
        return None
    
class MsSQLConnection(DbAPI2Connection):
    
    def __init__(self, *args, **kw):
        DbAPI2Connection.__init__(self, *args, **kw)
        self.coding_hint = "latin-1"
    
    def get_server_info(self):
        cur = self.cursor()
        cur.execute("SELECT @@VERSION")
        ver = cur.fetchall()[0][0]
        ver = ver.splitlines()[0].strip()+" - "+ver.splitlines()[-1].strip()
        cur.close()
        return ver
    
class MsSQLSchema(SchemaProvider):
    
    def q(self, connection, sql):
        cur = connection.cursor()._cur
        cur.execute(sql)
        return cur.fetchall()
    
    def fetch_children(self, connection, parent):
        if isinstance(parent, DatasourceInfo):
            return [SchemaCollection()]
        
        elif isinstance(parent, SchemaCollection):
            sql = "select catalog_name from information_schema.schemata"
            return [Schema(item[0]) for item in self.q(connection, sql)]
        
        elif isinstance(parent, Schema):
            return [TableCollection(schema=parent),
                    ViewCollection(schema=parent)]
        
        elif isinstance(parent, TableCollection):
            schema = parent.get_data("schema")
            sql = "select table_name from information_schema.tables \
            where table_type = 'BASE TABLE' \
            and table_catalog = '%s'" % schema.name
            return[Table(item[0], schema=schema)
                   for item in self.q(connection, sql)]
            
        elif isinstance(parent, ViewCollection):
            schema = parent.get_data("schema")
            sql = "select table_name from information_schema.tables \
            where table_type = 'VIEW' \
            and table_catalog = '%s'" % schema.name
            return[View(item[0], schema=schema)
                   for item in self.q(connection, sql)]
            
        elif isinstance(parent, (Table, View)):
            return [ColumnCollection(table=parent)]
        
        elif isinstance(parent, ColumnCollection):
            table = parent.get_data("table")
            schema = table.get_data("schema")
            sql = "select column_name from information_schema.columns \
            where table_catalog = '%s' and table_name = '%s'"
            sql = sql % (schema.name, table.name)
            return [Column(item[0], table=table)
                    for item in self.q(connection, sql)]


MsSQLBackend.INIT_ERROR = None
try:
    import pymssql
except ImportError:
    MsSQLBackend.INIT_ERROR = _(u"Python module pymssql not found.")