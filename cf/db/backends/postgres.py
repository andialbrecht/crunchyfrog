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

"""PostgreSQL backend."""

from cf.db import TRANSACTION_IDLE
from cf.db import TRANSACTION_COMMIT_ENABLED
from cf.db import TRANSACTION_ROLLBACK_ENABLED
from cf.db.backends import Generic, DEFAULT_OPTIONS, GUIOption
from cf.db import objects


class Postgres(Generic):

    drivername = 'postgres'

    @classmethod
    def get_options(cls):
        return DEFAULT_OPTIONS + (
            GUIOption('ssl_mode', _(u'SSL Mode'),
                      widget=GUIOption.WIDGET_COMBO,
                      choices=(
                          (None, None),
                          ('disable', _(u'No SSL (disable)')),
                          ('allow',
                           _(u'First try non SSL, then try SSL (allow)')),
                          ('prefer',
                           _(u'First try SSL, then non-SSL (prefer)')),
                          ('require',
                           _(u'Only try SSL connection (require)')),
                          )),
            )

    @classmethod
    def create_url(cls, options):
        url = super(Postgres, cls).create_url(options)
        if 'ssl_mode' in options and options['ssl_mode'] is not None:
            url.query = {'sslmode': options['ssl_mode']}
        return url

    @classmethod
    def get_native_shell_command(cls, url):
        args = []
        if url.username:
            args.extend(['-U', url.username])
        if url.database:
            args.extend(['-d', url.database])
        if url.host:
            args.extend(['-h', url.host])
        if url.port:
            args.extend(['-p', url.port])
        return 'psql', args

    @classmethod
    def dbapi(cls):
        import psycopg2
        return psycopg2

    @classmethod
    def get_connect_params(cls, url):
        opts = url.get_dict()
        if 'username' in opts:
            opts['user'] = opts['username']
            del opts['username']
        return tuple(), opts

    def prepare_connection(self, connection):
        import psycopg2.extensions as pe
        level = pe.ISOLATION_LEVEL_AUTOCOMMIT
        connection.connection.set_isolation_level(level)

    def get_server_info(self, connection):
        return connection.execute('select version()')[0][0]

    def _query(self, connection, sql):
        return connection.execute_raw(sql)

    def _get_search_path(self, connection):
        search_path = self._query(connection,
                                  'show search_path')[0][0].split(',')
        if '"$user"' in search_path:
            idx = search_path.index('"$user"')
            username = self._query(connection,
                                   'select current_user')[0][0]
            search_path[idx] = username
        return search_path

    def initialize(self, meta, connection):
        schemata = objects.Schemata(meta)
        users = objects.Users(meta)
        languages = objects.Languages(meta)
        meta.set_object(schemata)
        meta.set_object(users)
        meta.set_object(languages)
        search_path = self._get_search_path(connection)
        for item in self._query(connection, PG_INITIAL_SQL):
            if item['nspoid'] is not None:
                schema = meta.find_exact(oid=item['nspoid'],
                                              cls=objects.Schema,
                                              parent=schemata)
                if schema is None:
                    is_default = item['nspname'] in search_path
                    schema = objects.Schema(meta,
                                            oid=item['nspoid'],
                                            name=item['nspname'],
                                            comment=item['description'],
                                            parent=schemata,
                                            is_default=is_default)
                    meta.set_object(schema)
                    funcs = objects.Functions(meta, parent=schema)
                    meta.set_object(funcs)
            else:
                schema = None
            if item['objtype'] in ('table', 'view', 'sequence'):
                if item['objtype'] == 'table':
                    cls = objects.Table
                    coll_cls = objects.Tables
                elif item['objtype'] == 'sequence':
                    cls = objects.Sequence
                    coll_cls = objects.Sequences
                else:
                    cls = objects.View
                    coll_cls = objects.Views
                coll = meta.find_exact(cls=coll_cls,
                                       parent=schema)
                if coll is None:
                    coll = coll_cls(meta, parent=schema)
                    meta.set_object(coll)
                obj = cls(meta, schema=schema,
                          oid=item['reloid'], name=item['relname'],
                          comment=item['description'],
                          parent=coll)
                meta.set_object(obj)
            elif item['objtype'] == 'user':
                user = objects.User(meta, name=item['relname'],
                                    parent=users)
                meta.set_object(user)

    def refresh(self, obj, meta, connection):
        if obj.typeid == 'columns':
            self._refresh_columns(obj, meta, connection)
        elif obj.typeid == 'languages':
            self._refresh_languages(obj, meta, connection)
        elif obj.typeid == 'functions':
            self._refresh_functions(obj, meta, connection)

    def _refresh_columns(self, coll, meta, connection):
        table = coll.parent
        sql = ("select att.attnum, att.attname, dsc.description"
               " from pg_attribute att"
               " left join pg_description dsc on dsc.objoid = %(tableoid)s"
               "  and dsc.objsubid = att.attnum"
               " where att.attrelid = %(tableoid)s"
               " and att.attnum >= 1"
               % {"tableoid" : table.get_data("oid")})
        known_columns = {}
        [known_columns.setdefault(k.name, k)
         for k in meta.find(parent=coll, cls=objects.Column)]
        for item in self._query(connection, sql):
            col = known_columns.get(item['attname'], None)
            if col is None:
                col = objects.Column(meta, parent=coll)
            col.name = item['attname']
            col.pos = item['attnum']
            col.comment = item['description']
            meta.set_object(col)

    def _refresh_languages(self, coll, meta, connection):
        sql = "select lan.oid, lan.lanname from pg_language lan"
        for item in self._query(connection, sql):
            lan = meta.find_exact(parent=coll, oid=item['oid'])
            if lan is None:
                lan = objects.Language(meta, parent=coll,
                                       oid=item['oid'])
                meta.set_object(lan)
            lan.name = item['lanname']

    def _refresh_functions(self, coll, meta, connection):
        sql = ("select pro.oid, pro.proname, dsc.description"
               " from pg_proc pro"
               " left join pg_description dsc"
               "  on dsc.objoid = pro.oid"
               " where pro.pronamespace = %d" % coll.parent.oid)
        for item in self._query(connection, sql):
            pro = meta.find_exact(parent=coll, oid=item["oid"])
            if pro is None:
                pro = objects.Function(meta, parent=coll, oid=item["oid"])
                meta.set_object(pro)
            pro.name = item["proname"]
            pro.comment = item["description"]

    def get_transaction_state(self, connection):
        # The postgres backend retrieves this information from the
        # DB-API2 connection.
        psycopg2 = self.dbapi()
        conn = connection.get_dbapi_connection()
        stat = conn.get_transaction_status()
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
        return flag

    def begin(self, connection):
        connection.execute('BEGIN')
        return True

DRIVER = Postgres


PG_INITIAL_SQL = """
SELECT nsp.oid AS nspoid,
       nsp.nspname,
       rel.oid AS reloid,
       rel.relname,
       des.description,
       CASE WHEN rel.relkind = 'r' THEN 'table'
            WHEN rel.relkind = 'i' THEN 'index'
            WHEN rel.relkind = 'S' THEN 'sequence'
            WHEN rel.relkind = 'v' THEN 'view'
            ELSE rel.relkind::char  -- somehow this is required, otherwise the above fails
       END AS objtype --        rel.*

FROM pg_class rel
LEFT JOIN pg_description des ON des.objoid = rel.oid and des.objsubid is null
LEFT JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
WHERE rel.relkind IN ('v', 'r', 'S')

UNION

-- languages
SELECT NULL, NULL, lan.oid,
                   lan.lanname,
                   des.description, 'language'
FROM pg_language lan
LEFT JOIN pg_description des ON des.objoid = lan.oid

UNION

-- users
SELECT NULL, NULL, use.usesysid,
                   use.usename, NULL, 'user'
FROM pg_user use

union

-- functions
select nsp.oid, nsp.nspname, pro.oid, pro.proname, des.description, 'function'
from pg_proc pro
left join pg_namespace nsp on nsp.oid = pro.pronamespace
left join pg_description des on des.objoid = pro.oid
"""
