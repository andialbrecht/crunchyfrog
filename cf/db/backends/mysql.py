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

"""MySQL backend"""

import re

from cf.db import objects
from cf.db.backends import Generic, DEFAULT_OPTIONS

P_ERROR_MESSAGES = {
    1064: re.compile(r"near '(?P<pattern>.*)' at line (?P<lineno>\d+)$",
                     re.MULTILINE|re.UNICODE),
    1051: re.compile(r"Unknown table '(?P<pattern>.*)'$"),
    1146: re.compile(r"Table '.*\.(?P<pattern>.*)' doesn't exist$"),
    1054: re.compile(r"^Unknown column '(?P<pattern>.*)' in"),
}


class MySQL(Generic):

    drivername = 'mysql'

    @classmethod
    def dbapi(cls):
        import MySQLdb
        return MySQLdb

    @classmethod
    def get_native_shell_command(cls, url):
        args = []
        if url.user:
            args.extend(['-u', url.user])
        if url.password:
            args.extend(['--password=%s' % url.password])
        if url.host:
            args.extend(['-h', url.host])
        if url.port:
            args.extend(['-P', url.port])
        if url.database:
            args.extend(['-D', url.database])
        return 'mysql', args

    @classmethod
    def get_connect_params(cls, url):
        opts = url.get_dict()
        if 'database' in opts:
            opts['db'] = opts['database']
            del opts['database']
        if 'username' in opts:
            opts['user'] = opts['username']
            del opts['username']
        if 'password' in opts:
            opts['passwd'] = opts['password']
            del opts['password']
        opts.update(url.query)
        return tuple(), opts

    @classmethod
    def get_options(cls):
        return DEFAULT_OPTIONS

    @classmethod
    def create_url(cls, options):
        url = super(MySQL, cls).create_url(options)
        url.query = {'charset': 'utf8'}
        return url

    @classmethod
    def should_close(cls, error):
        if not isinstance(error, cls.dbapi().OperationalError):
            return False
        err_code, msg = error.args
        if err_code >= 2000:
            return True
        return False

    @classmethod
    def get_error_position(cls, query, error):
        err_code, msg = error.args
        p = P_ERROR_MESSAGES.get(err_code)
        print p
        if p is None:
            return None
        m = p.search(msg)
        print m
        if m is None:
            return None
        data = m.groupdict()
        line = data.get('lineno')
        pattern = data.get('pattern')
        print data
        if line is None and pattern is None:
            return None
        elif pattern is None:
            return int(line), 1
        if line is None:
            for idx, l in enumerate(query.statement.splitlines()):
                if pattern in l:
                    return idx+1, l.index(pattern)+1
        else:
            l = query.statement.splitlines()[int(line)-1]
            return int(line), l.index(pattern)+1

    def get_server_info(self, connection):
        return 'MySQL %s' % connection.connection.get_server_info()

    def initialize(self, meta, connection):
        schemata = objects.Schemata(meta)
        users = objects.Users(meta)
        meta.set_object(schemata)
        meta.set_object(users)
        for item in self._query(connection, INITIAL_SQL):
            if item['type'] == 'schema':
                schema = objects.Schema(meta, parent=schemata,
                                        oid=item['id'], name=item['name'],
                                        comment=item['description'])
                meta.set_object(schema)
                tables = objects.Tables(meta, parent=schema)
                meta.set_object(tables)
                schema.tables = tables
                views = objects.Views(meta, parent=schema)
                meta.set_object(views)
                schema.views = views

            if item['type'] in ('BASE TABLE', 'VIEW', 'SYSTEM VIEW'):
                schema = meta.find_exact(cls=objects.Schema,
                                         oid=item['parent'])
                if item['type'] == 'BASE TABLE':
                    cls = objects.Table
                    parent = meta.find_exact(cls=objects.Tables, parent=schema)
                else:
                    cls = objects.View
                    parent = meta.find_exact(cls=objects.Views, parent=schema)
                obj = cls(meta, parent=parent, oid=item['id'],
                          name=item['name'], comment=item['description'])
                meta.set_object(obj)

            if item['type'] == 'column':
                parent = meta.find_exact(oid=item['parent'])
                col = objects.Column(meta, parent=parent.columns,
                                     oid=item['id'],
                                     name=item['name'],
                                     comment=item['description'])
                meta.set_object(col)

    def _query(self, connection, sql):
        return connection.execute_raw(sql)

    def refresh(self, obj, meta, connection):
        if obj.typeid == 'users':
            self._refresh_users(obj, meta, connection)
        elif obj.typeid == 'constraints':
            self._refresh_constraints(obj, meta, connection)

    def _refresh_constraints(self, coll, meta, connection):
        sql = ("select lower(concat(table_schema, '.', table_name)) as parent,"
               "lower(concat(table_schema, '.', table_name, '.',"
               " constraint_name)) as id,"
               " case when constraint_type = 'PRIMARY KEY'"
               " then constraint_type"
               " else concat(constraint_type, ' (', constraint_name, ')')"
               " end as name"
               " from information_schema.table_constraints"
               " where lower(table_name) = '%s'"
               "  and lower(table_schema) = '%s'"
               % (coll.parent.name.lower(),
                  coll.parent.parent.parent.name.lower()))
        for item in self._query(connection, sql):
            print item['id'], item['parent']
            con = meta.find_exact(oid=item['id'],
                                  parent=coll.parent.constraints)
            if con is None:
                con = objects.Constraint(meta, parent=coll.parent.constraints,
                                         oid=item['id'])
                meta.set_object(con)
            con.name = item['name']

    def _refresh_users(self, coll, meta, connection):
        sql = "select concat(user, '@', host) as name from mysql.user"
        for item in self._query(connection, sql):
            user = meta.find_exact(parent=coll, name=item['name'])
            if user is None:
                user = objects.User(meta, parent=coll, name=item['name'])
                user.props.has_children = False
                meta.set_object(user)


DRIVER = MySQL

INITIAL_SQL = """select * from (
select lower(schema_name) as id, schema_name as name,
null as description, 'schema' as type, null as parent, 0 as pos
from information_schema.schemata
union
select lower(concat(table_schema, '.', table_name)) as id,
table_name as name, table_comment as description, table_type as type,
lower(table_schema) as parent, 1 as pos
from information_schema.tables
union
select lower(concat(table_schema, '.', table_name, '.', column_name)) as id,
column_name as name, column_comment as description, 'column' as type,
lower(concat(table_schema, '.', table_name)) as parent, 3 as pos
from information_schema.columns
) x order by pos asc
"""
