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

from cf.db.backends import Generic, DEFAULT_OPTIONS


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

    def get_server_info(self, connection):
        return 'MySQL %s' % connection.connection.get_server_info()


DRIVER = MySQL
