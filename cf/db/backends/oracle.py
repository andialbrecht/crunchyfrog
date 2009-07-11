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

"""Oracle backend"""

from cf.db import objects
from cf.db.backends import Generic, GUIOption


class Oracle(Generic):

    drivername = 'oracle'

    @classmethod
    def dbapi(cls):
        import cx_Oracle
        return cx_Oracle

    @classmethod
    def get_native_shell_command(cls, url):
        args = []
        logon = ''
        if url.user:
            logon += url.user
        if url.password:
            logon += '/%s' % url.password
        if url.host:
            logon += '@%s' % url.host
        if 'mode' in url.query and url.query['mode']:
            logon += ' AS %s' % url.query['mode']
        args.extend([logon])
        return 'sqlplus', args

    @classmethod
    def get_connect_params(cls, url):
        # derived from sqlalchemy.databases.oracle
        if url.database:
            # if we have a database, then we have a remote host
            port = url.port
            if port:
                port = int(port)
            else:
                port = 1521
            dsn = self.dbapi().makedsn(url.host, port, url.database)
        else:
            # we have a local tnsname
            dsn = url.host

        opts = dict(user=url.username, password=url.password, dsn=dsn)
        if 'mode' in url.query:
            opts['mode'] = url.query['mode']
            if isinstance(opts['mode'], basestring):
                mode = opts['mode'].upper()
                if mode == 'SYSDBA':
                    opts['mode'] = self.dbapi().SYSDBA
                elif mode == 'SYSOPER':
                    opts['mode'] = self.dbapi().SYSOPER
                else:
                    opts['mode'] = int(opt['mode'])
        return tuple(), opts

    @classmethod
    def get_options(cls):
        return (
            GUIOption('host', _(u'TNS Name')),
            GUIOption('username', _(u'Username')),
            GUIOption('password', _(u'Password'),
                      widget=GUIOption.WIDGET_PASSWORD),
            GUIOption('mode', _(u'Mode'),
                      widget=GUIOption.WIDGET_COMBO,
                      choices=(
                          (None, None),
                          ('SYSDBA', 'SYSDBA'),
                          ('SYSOPER', 'SYSOPER'),
                      )),
            )

    def get_server_info(self, connection):
        return 'Oracle %s' % connection.connection.version

    def prepare_statement(self, sql):
        # See issue50: cx_Oracle requires str or None for cursor.execute().
        sql = str(sql)
        # Another issue: Somehow Oracle dislikes trailing semicolons.
        # Maybe this approach is a little bit crude, but just remove it...
        # See this thread for example:
        # http://www.mail-archive.com/django-users@googlegroups.com/msg11479.html
        sql = sql.strip()
        if sql.endswith(';'):
            sql = sql[:-1]
        return str(sql)

    def get_explain_statement(self, statement):
        return ['explain plan for %s' % statement, 'select * from plan_table']

    def _query(self, connection, sql):
        return connection.execute_raw(sql)

    def initialize(self, meta, connection):
        schemata = objects.Schemata(meta)
        users = objects.Users(meta)
        meta.set_object(schemata)
        meta.set_object(users)
        tbl_cache = {}  # speed up object creation
        for item in self._query(connection, INITIAL_SQL):
            if item['TYPE'] == 'schema':
                schema = objects.Schema(meta, oid=item['ID'],
                                        name=item['NAME'], parent=schemata)
                meta.set_object(schema)
                tables = objects.Tables(meta, parent=schema)
                meta.set_object(tables)
                schema.tables = tables
                views = objects.Views(meta, parent=schema)
                meta.set_object(views)
                schema.views = views
                schema.sequences = objects.Sequences(meta, parent=schema)
                meta.set_object(schema.sequences)

            if item['TYPE'] in ('table', 'view'):
                schema = meta.find_exact(cls=objects.Schema,
                                         oid=item['PARENT'])
                if item['TYPE'] == 'table':
                    cls = objects.Table
                    parent = meta.find_exact(cls=objects.Tables, parent=schema)
                else:
                    cls = objects.View
                    parent = meta.find_exact(cls=objects.Views, parent=schema)
                obj = cls(meta, parent=parent, oid=item['ID'],
                          name=item['NAME'], comment=item['DESCRIPTION'])
                meta.set_object(obj)
                tbl_cache[item['ID']] = obj
                if item['TYPE'] == 'table':
                    obj.indexes = objects.Indexes(meta, parent=obj)
                    meta.set_object(obj.indexes)
                obj.triggers = objects.Triggers(meta, parent=obj)
                meta.set_object(obj.triggers)

            if item['TYPE'] == 'column':
                parent = tbl_cache.get(item['PARENT'])
                if parent is None:
                    continue
                col = objects.Column(meta, parent=parent.columns,
                                     oid=item['ID'],
                                     name=item['NAME'],
                                     comment=item['DESCRIPTION'])
                meta.set_object(col)


    def refresh(self, obj, meta, connection):
        if obj.typeid == 'users':
            self._refresh_users(obj, meta, connection)
        elif obj.typeid == 'constraints':
            self._refresh_constraints(obj, meta, connection)
        elif obj.typeid == 'indexes':
            self._refresh_indexes(obj, meta, connection)
        elif obj.typeid == 'triggers':
            self._refresh_triggers(obj, meta, connection)
        elif obj.typeid == 'sequences':
            self._refresh_sequences(obj, meta, connection)

    def _refresh_users(self, coll, meta, connection):
        sql = "select username from sys.all_users"
        for item in self._query(connection, sql):
            u = meta.find_exact(parent=coll, oid=item['USERNAME'].lower())
            if u is None:
                u = objects.User(meta, parent=coll,
                                 oid=item['USERNAME'].lower(),
                                 name=item['USERNAME'])
                meta.set_object(u)
                u.props.has_children = False

    def _refresh_constraints(self, coll, meta, connection):
        sql = ("select lower(owner||'.'||constraint_name) as id,"
               " constraint_name as name"
               " from sys.all_constraints"
               " where lower(owner||'.'||table_name) = '%s'"
               % coll.parent.oid)
        for item in self._query(connection, sql):
            con = meta.find_exact(parent=coll, oid=item['ID'])
            if con is None:
                con = objects.Constraint(meta, parent=coll,
                                         oid=item['ID'])
                meta.set_object(con)
            con.name = item['NAME']
            con.pros.has_children = False

    def _refresh_indexes(self, coll, meta, connection):
        sql = ("select lower(owner||'.'||index_name) as id,"
               " index_name as name from sys.all_indexes"
               " where lower(owner||'.'||table_name) = '%s'"
               % coll.parent.oid)
        for item in self._query(connection, sql):
            con = meta.find_exact(parent=coll, oid=item['ID'])
            if con is None:
                con = objects.Index(meta, parent=coll,
                                    oid=item['ID'])
                meta.set_object(con)
            con.name = item['NAME']
            con.props.has_children = False

    def _refresh_triggers(self, coll, meta, connection):
        sql = ("select lower(owner||'.'||trigger_name) as id,"
               " trigger_name as name"
               " from sys.all_triggers"
               " where lower(owner||'.'||table_name) = '%s'"
               % coll.parent.oid)
        for item in self._query(connection, sql):
            con = meta.find_exact(parent=coll, oid=item['ID'])
            if con is None:
                con = objects.Trigger(meta, parent=coll,
                                      oid=item['ID'])
                meta.set_object(con)
            con.name = item['NAME']
            con.props.has_children = False

    def _refresh_sequences(self, coll, meta, connection):
        sql = ("select lower(sequence_owner||'.'||sequence_name) as id,"
               " sequence_name as name"
               " from sys.all_sequences"
               " where lower(sequence_owner) = '%s'"
               % coll.parent.oid)
        for item in self._query(connection, sql):
            seq = meta.find_exact(parent=coll, oid=item['ID'])
            if seq is None:
                seq = objects.Sequence(meta, parent=coll, oid=item['ID'])
                meta.set_object(seq)
            seq.name = item['NAME']
            seq.props.has_children = False


DRIVER = Oracle


INITIAL_SQL = """select * from (
select lower(username) as id, null as parent,
username as name, null as description, 'schema' as type, 1 as pos
from sys.all_users
where exists (select 'x' from sys.all_objects where owner=username) or username = user

union

select
lower(t.owner||'.'||t.table_name) as id, lower(t.owner) as parent,
t.table_name as name, c.comments as description, 'table' as type, 2 as pos
from sys.all_tables t
left join all_tab_comments c on c.owner = t.owner
and c.table_name = t.table_name
and c.table_type = 'TABLE'

union

select
lower(t.owner||'.'||t.view_name) as id, lower(t.owner) as parent,
t.view_name as name, c.comments as description, 'table' as type, 3 as pos
from sys.all_views t
left join all_tab_comments c on c.owner = t.owner
and c.table_name = t.view_name
and c.table_type = 'VIEW'

union

select
lower(t.owner||'.'||t.table_name||'.'||t.column_name) as id,
lower(t.owner||'.'||t.table_name) as parent,
t.column_name as name, c.comments as description, 'column' as type, 4 as pos
from sys.all_tab_columns t
left join sys.all_col_comments c on c.owner = t.owner
and c.table_name = t.table_name and c.column_name = t.column_name
) x order by pos, name"""
