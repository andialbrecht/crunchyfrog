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

"""PostgreSQL backend"""

import gtk
import gobject

from cf.backends import DBConnectError, TRANSACTION_IDLE, TRANSACTION_COMMIT_ENABLED, TRANSACTION_ROLLBACK_ENABLED
from cf.backends.dbapi2helper import DbAPI2Connection, DbAPI2Cursor
from cf.backends.schema import *
from cf.backends import ReferenceProvider
from cf.datasources import DatasourceInfo
from cf.plugins.core import DBBackendPlugin
from cf.utils import Emit

import time
from urllib import quote_plus


from gettext import gettext as _

import logging
log = logging.getLogger("PG")


class PgReferenceProvider(ReferenceProvider):
    name = _(u"PostgreSQL Reference")
    base_url = "http://www.postgresql.org/docs/current"

    def get_context_help_url(self, term):
        url = "http://search.postgresql.org/search?u=%2Fdocs%2F8.3%2Finteractive%2F&q="
        url += quote_plus(term.strip())
        return url


class PostgresBackend(DBBackendPlugin):

    id = "crunchyfrog.backend.postgres"
    name = _(u"PostgreSQL Plugin")
    description = _(u"Provides access to PostgreSQL databases")
    password_option = "password"

    def __init__(self, app):
        DBBackendPlugin.__init__(self, app)
        log.info("Activating PostgreSQL backend")
        self.schema = PgSchema()
        self.reference = PgReferenceProvider()
        self.features.transactions = True

    def _get_conn_opts_from_opts(self, opts):
        conn_opts = dict()
        if opts["database"]: conn_opts["database"] = opts["database"]
        if opts["host"]: conn_opts["host"] = opts["host"]
        if opts["port"]: conn_opts["port"] = opts["port"]
        if opts["user"]: conn_opts["user"] = opts["user"]
        if opts["password"]: conn_opts["password"] = opts["password"]
        return conn_opts

    def shutdown(self):
        log.info("Shutting down PostgreSQL backend")

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
            import psycopg2
        except ImportError:
            raise DBConnectError(_(u"Python module psycopg2 is not installed."))
        try:
            real_conn = psycopg2.connect(**opts)
            real_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        except StandardError, err:
            raise DBConnectError(str(err))
        conn = PgConnection(self, self.app, real_conn)
        conn.threadsafety = psycopg2.threadsafety
        return conn

    def test_connection(self, data):
        try:
            conn = self.dbconnect(data)
            conn.close()
        except DBConnectError, err:
            return str(err)
        return None


class PgCursor(DbAPI2Cursor):

    def __init__(self, *args, **kw):
        DbAPI2Cursor.__init__(self, *args, **kw)
        self._notice_tag = None

    def _check_notices(self):
        return
        while self.connection._conn.notices:
            gobject.idle_add(self.connection.emit, "notice", self.connection._conn.notices.pop())
            #Emit(self.connection, "notice", self.connection._conn.notices.pop())

    def execute(self, *args, **kw):
        #gtk.gdk.threads_enter()
        #self._notice_tag = gobject.timeout_add(100, self._check_notices)
        #gtk.gdk.threads_leave()
        DbAPI2Cursor.execute(self, *args, **kw)
        #gtk.gdk.threads_enter()
        #gobject.source_remove(self._notice_tag)
        #gtk.gdk.threads_leave()
        #self._check_notices()

    def get_messages(self):
        ret = []
        while self.connection._conn.notices:
            ret.append(self.connection._conn.notices.pop())
        if self._cur.statusmessage:
            ret.append(self._cur.statusmessage)
        return ret


class PgConnection(DbAPI2Connection):
    cursor_class = PgCursor

    def update_transaction_status(self):
        stat = self._conn.get_transaction_status()
        if stat == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
            flag = TRANSACTION_ROLLBACK_ENABLED
        elif stat == psycopg2.extensions.TRANSACTION_STATUS_ACTIVE:
            flag = TRANSACTION_IDLE
        elif stat == psycopg2.extensions.TRANSACTION_STATUS_IDLE:
            flag = TRANSACTION_IDLE
        elif stat == psycopg2.extensions.TRANSACTION_STATUS_INTRANS:
            flag = TRANSACTION_COMMIT_ENABLED|TRANSACTION_ROLLBACK_ENABLED
        else:
            flag = TRANSACTION_IDLE
        self.props.transaction_state = flag

    def get_server_info(self):
        cur = self._conn.cursor()
        cur.execute("select version()")
        ret = cur.fetchone()
        cur.close()
        return ret[0]

class PgLanguageCollection(Collection):
    name = _(u"Languages")

class PgLanguage(Node):
    name = _(u"Language")
    icon = "stock_script"
    has_children = False

class PgSchema(SchemaProvider):

    def __init__(self):
        SchemaProvider.__init__(self)

    def q(self, connection, sql):
        cur = connection.cursor()._cur
        cur.execute(sql)
        return cur.fetchall()

    def fetch_children(self, connection, parent):
        if isinstance(parent, DatasourceInfo):
            return [SchemaCollection(),
                    PgLanguageCollection()]

        elif isinstance(parent, SchemaCollection):
            ret = []
            sql = "select nsp.oid, nsp.nspname, dsc.description \
            from pg_namespace nsp \
            left join pg_description dsc on dsc.objoid = nsp.oid \
            where nsp.nspname not like 'pg_%' and nsp.nspname != 'information_schema'"
            for item in self.q(connection, sql):
                s = Schema(item[1], item[2])
                s.set_data("oid", item[0])
                ret.append(s)
            return ret

        elif isinstance(parent, Schema):
            return [TableCollection(schema=parent),
                    ViewCollection(schema=parent),
                    SequenceCollection(schema=parent),
                    FunctionCollection(schema=parent)]

        elif isinstance(parent, TableCollection) \
        or isinstance(parent, ViewCollection) \
        or isinstance(parent, SequenceCollection):
            if isinstance(parent, TableCollection):
                obj = Table
                relkind = 'r'
                has_details = False
            elif isinstance(parent, ViewCollection):
                obj = View
                relkind = 'v'
                has_details = True
            elif isinstance(parent, SequenceCollection):
                obj = Sequence
                relkind = 'S'
                has_details = False
            schema = parent.get_data("schema")
            sql = "select rel.oid, rel.relname, dsc.description from pg_class rel \
            left join pg_description dsc on dsc.objoid = rel.oid and dsc.objsubid = 0 \
            where rel.relnamespace = %(nspoid)s \
            and rel.relkind = '%(relkind)s'" % {"nspoid" : schema.get_data("oid"),
                                                "relkind" : relkind}
            ret = []
            for item in self.q(connection, sql):
                ret.append(obj(item[1], item[2], oid=item[0],
                               has_details=has_details))
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
            sql = "select att.attnum, att.attname, dsc.description from pg_attribute att \
            left join pg_description dsc on dsc.objoid = %(tableoid)s and dsc.objsubid = att.attnum \
            where att.attrelid = %(tableoid)s \
            and att.attnum >= 1" % {"tableoid" : table.get_data("oid")}
            for item in self.q(connection, sql):
                ret.append(Column(item[1], item[2], attnum=item[0]))
            return ret

        elif isinstance(parent, FunctionCollection):
            ret = []
            schema = parent.get_data("schema")
            sql = "select pro.oid, pro.proname, dsc.description from pg_proc pro \
            left join pg_description dsc on dsc.objoid = pro.oid \
            where pro.pronamespace = %(schemaoid)s" % {"schemaoid" : schema.get_data("oid")}
            for item in self.q(connection, sql):
                ret.append(Function(item[1], item[2], oid=item[0]))
            return ret

        elif isinstance(parent, ConstraintCollection):
            ret = []
            table = parent.get_data("table")
            sql = "select con.oid, con.conname \
            from pg_constraint con \
            where con.conrelid = %(relid)s" % {"relid" : table.get_data("oid")}
            for item in self.q(connection, sql):
                ret.append(Constraint(item[1], oid=item[0]))
            return ret

        elif isinstance(parent, IndexCollection):
            ret = []
            table = parent.get_data("table")
            sql = "select rel.oid, rel.relname, dsc.description \
            from pg_class rel \
            left join pg_description dsc on dsc.objoid = rel.oid \
            , pg_index ind \
            where ind.indrelid = %(relid)s and ind.indexrelid = rel.oid" % {"relid" : table.get_data("oid")}
            for item in self.q(connection, sql):
                ret.append(Index(item[1], item[2], oid=item[0]))
            return ret

        elif isinstance(parent, PgLanguageCollection):
            sql = "select lan.oid, lan.lanname, dsc.description \
            from pg_language lan \
            left join pg_description dsc on dsc.objoid = lan.oid"
            return [PgLanguage(item[1], item[2], oid=item[0]) for item in self.q(connection, sql)]

    def get_details(self, connection, obj):
        func = getattr(self, "details_%s" % obj.__class__.__name__.lower(), None)
        if func:
            return func(connection, obj)
        return None

    def details_view(self, connection, view):
        ret = dict()
        sql = "select pg_get_viewdef(%(oid)s, true)" %{"oid" : view.get_data("oid")}
        res = self.q(connection, sql)
        ret[_(u"Definition")] =  res[0][0]
        return ret


try:
    import psycopg2
    import psycopg2.extensions
except ImportError:
    PostgresBackend.INIT_ERROR = _(u"Python module psycopg2 required.")
