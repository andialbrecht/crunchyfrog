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

from cf.backends import DBConnection, DBCursor

class DbAPI2Connection(DBConnection):
    
    def __init__(self, app, real_conn):
        DBConnection.__init__(self, app)
        self._conn = real_conn
        
    def close(self):
        self._conn.close()
        DBConnection.close(self)
        
    def cursor(self):
        return DbAPI2Cursor(self)
    
class DbAPI2Cursor(DBCursor):
    
    def __init__(self, connection):
        DBCursor.__init__(self, connection)
        self._cur = self.connection._conn.cursor()
        
    def _get_description(self):
        return self._cur.description
    description = property(fget=_get_description)
    
    def _get_rowcount(self):
        return self._cur.rowcount
    rowcount = property(fget=_get_rowcount)
        
    def execute(self, statement):
        self._cur.execute(statement)
        
    def fetchall(self):
        return self._cur.fetchall()