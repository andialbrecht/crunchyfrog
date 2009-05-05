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

"""MySQL backend"""


from cf.backends import DBConnectError
from cf.backends.dbapi2helper import DbAPI2Connection
from cf.backends.schema import *
from cf.datasources import DatasourceInfo
from cf.plugins.core import DBBackendPlugin

import time
from urllib import quote_plus

from gettext import gettext as _

import logging
log = logging.getLogger("MYSQL")

class MySQLBackend(DBBackendPlugin):

    id = "crunchyfrog.backend.mysql"
    name = _(u"MySQL Plugin")
    description = _(u"Provides access to MySQL databases")
    password_option = "password"

    def __init__(self, app):
        DBBackendPlugin.__init__(self, app)
        log.info("Activating MySQL backend")
        self.schema = MySQLSchema()
        self.features.transactions = True

    def _get_conn_opts_from_opts(self, opts):
        conn_opts = dict()
        if opts["database"]: conn_opts["db"] = opts["database"]
        if opts["host"]: conn_opts["host"] = opts["host"]
        if opts["port"]: conn_opts["port"] = opts["port"]
        if opts["user"]: conn_opts["user"] = opts["user"]
        if opts["password"]: conn_opts["passwd"] = opts["password"]
        return conn_opts

    def shutdown(self):
        log.info("Shutting down MySQL backend")

    @classmethod
    def get_datasource_options_widgets(cls, data_widgets, initial_data=None):
        return data_widgets, ["host", "port", "database", "user", "password"]

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
            import MySQLdb
        except ImportError:
            raise DBConnectError(_(u"Python module MySQLdb is not installed."))
        try:
            real_conn = MySQLdb.connect(**opts)
        except StandardError, err:
            raise DBConnectError(str(err))
        conn = MySQLConnection(self, self.app, real_conn)
        conn.threadsafety = MySQLdb.threadsafety
        return conn

    def test_connection(self, data):
        try:
            conn = self.dbconnect(data)
            conn.close()
        except DBConnectError, err:
            return str(err)
        return None

class MySQLConnection(DbAPI2Connection):

    def get_server_info(self):
        return "MySQL %s" % self._conn.get_server_info()

class MySQLSchema(SchemaProvider):

    def q(self, connection, sql):
        cur = connection.cursor()._cur
        cur.execute(sql)
        return cur.fetchall()

    def fetch_children(self, connection, parent):
        if isinstance(parent, DatasourceInfo):
            return [SchemaCollection()]

        elif isinstance(parent, SchemaCollection):
            ret = []
            sql = "select schema_name from information_schema.schemata"
            for item in self.q(connection, sql):
                ret.append(Schema(item[0]))
            return ret

        elif isinstance(parent, Schema):
            return [TableCollection(schema=parent),
                    ViewCollection(schema=parent)]

        elif isinstance(parent, TableCollection) \
        or isinstance(parent, ViewCollection):
            if isinstance(parent, TableCollection):
                obj = Table
                kind = "BASE TABLE"
            elif isinstance(parent, ViewCollection):
                obj = View
                kind = "VIEW"
            ret = []
            schema = parent.get_data("schema")
            sql = ('select table_name, table_comment '
                   'from information_schema.tables '
                   'where table_schema = \'%(schema)s\' '
                   'and table_type = \'%(kind)s\''
                   % {"schema" : schema.name, "kind" : kind})
            for item in self.q(connection, sql):
                ret.append(obj(item[0], item[1], schema=schema))
            return ret

        elif isinstance(parent, Table):
            return [ColumnCollection(table=parent)]

        elif isinstance(parent, View):
            return [ColumnCollection(table=parent)]

        elif isinstance(parent, ColumnCollection):
            ret = []
            table = parent.get_data("table")
            sql = ("select column_name, column_comment "
                   "from information_schema.columns "
                   "where table_name = '%(table)s' "
                   "and table_schema = '%(schema)s'"
                   % {"table" : table.name,
                      "schema": table.get_data("schema").name})
            for item in self.q(connection, sql):
                ret.append(Column(item[0], item[1], table=table))
            return ret


try:
    import MySQLdb
except ImportError:
    MySQLBackend.INIT_ERROR = _(u"Python module MySQLdb required.")
