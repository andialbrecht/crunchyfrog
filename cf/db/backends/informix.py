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

"""Informix backend."""

from cf.db.backends import Generic, DEFAULT_OPTIONS


class Informix(Generic):

    drivername = 'informix'

    @classmethod
    def dbapi(cls):
        import informixdb
        return informixdb

    @classmethod
    def get_connect_params(cls, url):
        # copied from sqlalchemy.databases.informix
        if url.host:
            dsn = '%s@%s' % ( url.database , url.host )
        else:
            dsn = url.database

        if url.username:
            opt = { 'user':url.username , 'password': url.password }
        else:
            opt = {}

        return ([dsn], opt)

    @classmethod
    def get_options(cls):
        return DEFAULT_OPTIONS


DRIVER = Informix
