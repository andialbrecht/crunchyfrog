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

"""Firebird backend."""

from cf.db import objects
from cf.db.backends import Generic, DEFAULT_OPTIONS


class Firebird(Generic):

    drivername = 'firebird'

    @classmethod
    def dbapi(cls):
        import firebirdsql
        return firebirdsql

    @classmethod
    def get_native_shell_command(cls, url):
        args = []
        if url.username:
            args.extend(['-u', url.username])
        if url.password:
            args.extend(['-p', url.password])
        if url.host and url.port and url.database:
            args.extend(['%s/%d:%s' % (url.host, url.port, url.database)])
        elif url.host and url.database:
            args.extend(['%s:%s' % (url.host, url.database)])
        else:
            args.extend(['127.0.0.1:' + url.database])
        return 'isql-fb', args

    @classmethod
    def get_connect_params(cls, url):
        opts = url.get_dict()
        if 'username' in opts:
            opts['user'] = opts['username']
            del opts['username']
        if opts.get('port'):
            opts['host'] = "%s/%s" % (opts['host'], opts['port'])
            del opts['port']
        opts.update(url.query)

        if not cls.dbapi().initialized:
            cls.dbapi().init()

        return ([], opts)

    @classmethod
    def get_options(cls):
        return DEFAULT_OPTIONS

    def get_server_info(self, connection):
        sql = 'select rdb$get_context("SYSTEM", "ENGINE_VERSION") from rdb$database'
        return 'FirebirdSQL ' + connection.execute(sql)[0][0]

    def initialize(self, meta, connection):
        tables = objects.Tables(meta)
        meta.set_object(tables)
        views = objects.Views(meta)
        meta.set_object(views)
        sql = 'select rdb$relation_name, rdb$view_blr ' \
            'from rdb$relations where rdb$system_flag=0'
        for item in connection.execute(sql):
            if not item[1]:
                table = objects.Table(meta, name=item[0], parent=tables)
                meta.set_object(table)
            else:
                view = objects.View(meta, name=item[0], parent=views)
                meta.set_object(view)
        users = objects.Users(meta)
        meta.set_object(users)
        sql = 'select distinct rdb$user from rdb$user_privileges'
        for item in connection.execute(sql):
            user = objects.User(meta, name=item[0], parent=users)
            meta.set_object(user)
        functions = objects.Functions(meta)
        meta.set_object(functions)
        sql = 'select rdb$function_name from rdb$functions where rdb$system_flag=0'
        for item in connection.execute(sql):
            function = objects.User(meta, name=item[0], parent=functions)
            meta.set_object(function)

    def get_explain_statement(self, statement):
        return None


DRIVER = Firebird
