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

# $Id: oracle.py 109 2008-03-17 19:29:34Z albrecht.andi $

"""Oracle backend"""


from cf.backends import DBConnectError
from cf.backends.dbapi2helper import DbAPI2Connection, DbAPI2Cursor
from cf.backends.schema import *
from cf.datasources import DatasourceInfo
from cf.plugins.core import DBBackendPlugin

import time

from gettext import gettext as _

import logging
log = logging.getLogger("ORACLE")

class OracleBackend(DBBackendPlugin):
    id = "crunchyfrog.backend.oracle"
    name = _(u"Oracle Plugin")
    description = _(u"Provides access to Oracle databases")
    
    def __init__(self, app):
        DBBackendPlugin.__init__(self, app)
        log.info("Activating Oracle backend")
        self.schema = OracleSchema()
        
    def _get_conn_opts_from_opts(self, opts):
        conn_opts = dict()
        if opts["database"]: conn_opts["dsn"] = opts["database"]
        if opts["user"]: conn_opts["user"] = opts["user"]
        if opts["password"]: conn_opts["password"] = opts["password"]
        return conn_opts
        
    def shutdown(self):
        log.info("Shutting down Oracle backend")
    
    @classmethod
    def get_datasource_options_widgets(cls, data_widgets, initial_data=None):
        return data_widgets, ["database", "user", "password"]
    
    @classmethod
    def get_label(cls, datasource_info):
        s = "%s@%s" % (datasource_info.options.get("user", None) or "??",
                       datasource_info.options.get("database", None) or "??")
        if datasource_info.name:
            s = '%s (%s)' % (datasource_info.name, s)
        return s
    
    def dbconnect(self, data):
        opts = self._get_conn_opts_from_opts(data)
        if data.get("ask_for_password", False):
            pwd = self.password_prompt()
            if not pwd:
                raise DBConnectError(_(u"No password given."))
            opts["password"] = pwd
        try:
            import cx_Oracle
        except ImportError:
            raise DBConnectError(_(u"Python module cx_Oracle is not installed."))
        try:
            real_conn = cx_Oracle.connect(**opts)
        except StandardError, err:
            raise DBConnectError(str(err))
        conn = OracleConnection(self, self.app, real_conn)
        conn.threadsafety = cx_Oracle.threadsafety
        return conn
    
    def test_connection(self, data):
        try:
            conn = self.dbconnect(data)
            conn.close()
        except DBConnectError, err:
            return str(err)
        return None
    
class OracleCursor(DbAPI2Cursor):
    
    def __init__(self, *args, **kw):
        DbAPI2Cursor.__init__(self, *args, **kw)
        self._fetched = None
        
    def fetchall(self):
        if self._fetched == None:
            self._fetched = self._cur.fetchall()
        return self._fetched
    
    def execute(self, statement):
        DbAPI2Cursor.execute(self, statement)
        self.fetchall()
    
    def _get_rowcount(self):
        if self._fetched == None:
            return -1
        return len(self._fetched)
    rowcount = property(fget=_get_rowcount)
    
class OracleConnection(DbAPI2Connection):
    cursor_class = OracleCursor
    
    def get_server_info(self):
        return "Oracle %s" % self._conn.version
    
    
class OracleSchema(SchemaProvider):
    
    def q(self, connection, sql):
        cur = connection.cursor()._cur
        cur.execute(sql)
        return cur.fetchall()
    
    def fetch_children(self, connection, parent):
        if isinstance(parent, DatasourceInfo):
            return [TableCollection(),
                    ViewCollection(),
                    SequenceCollection(),
                    PackageCollection()]
        
        elif isinstance(parent, TableCollection):
            ret = []
            sql = "select t.table_name, c.comments \
            from user_tables t \
            left join user_tab_comments c on c.table_name = t.table_name \
            and c.table_type = 'TABLE'"
            for item in self.q(connection, sql):
                ret.append(Table(item[0], item[1]))
            return ret
        
        elif isinstance(parent, ViewCollection):
            ret = []
            sql = "select t.view_name, c.comments from user_views t \
            left join user_tab_comments c on c.table_name = t.view_name \
            and c.table_type = 'VIEW'"
            for item in self.q(connection, sql):
                ret.append(View(item[0]))
            return ret
        
        elif isinstance(parent, Table):
            return [ColumnCollection(table=parent),
                    ConstraintCollection(table=parent),
                    IndexCollection(table=parent)]
        
        elif isinstance(parent, View):
            return [ColumnCollection(table=parent)]
        
        elif isinstance(parent, ColumnCollection):
            table = parent.get_data("table")
            ret = []
            sql = "select col.column_name, com.comments \
            from user_tab_columns col \
            left join user_col_comments com on com.table_name = '%(table)s' and com.column_name = col.column_name \
            where col.table_name = '%(table)s'" % {"table" : table.name}
            [ret.append(Column(item[0], item[1])) for item in self.q(connection, sql)]
            return ret
        
        elif isinstance(parent, ConstraintCollection):
            table = parent.get_data("table")
            ret = []
            sql = "select constraint_name from user_constraints \
            where table_name = '%(table)s'" % {"table" : table.name}
            [ret.append(Constraint(item[0])) for item in self.q(connection, sql)]
            return ret
        
        elif isinstance(parent, IndexCollection):
            table = parent.get_data("table")
            ret = []
            sql = "select index_name from user_indexes \
            where table_name = '%(table)s'" % {"table" : table.name}
            [ret.append(Index(item[0])) for item in self.q(connection, sql)]
            return ret
        
        elif isinstance(parent, SequenceCollection):
            ret = []
            sql = "select sequence_name from user_sequences"
            [ret.append(Sequence(item[0])) for item in self.q(connection, sql)]
            return ret
        
        # FIXME: Cleanup packages and procedures
        elif isinstance(parent, PackageCollection):
            ret = []
            sql = "select distinct object_name from user_procedures \
            where object_name is not null"
            [ret.append(Package(item[0])) for item in self.q(connection, sql)]
            return ret
        
        elif isinstance(parent, Package):
            ret = []
            sql = "select procedure_name from user_procedures \
            where object_name = '%(package)s'" % {"package": parent.name}
            [ret.append(Function(item[0])) for item in self.q(connection, sql)]
            return ret


try:
    import cx_Oracle
except ImportError:
    OracleBackend.INIT_ERROR = _(u"Python module cx_Oracle required.")