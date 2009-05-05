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


DRIVER = MSSql
