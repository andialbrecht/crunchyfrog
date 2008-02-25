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

# $Id: __init__.py 130 2008-02-25 13:25:18Z freshi $

"""Database backends"""

import gobject
import gtk

import sys


class DBError(StandardError):
    """Base class for database errors"""

class DBConnectError(DBError):
    """Errors on opening a connection"""
    
class DBConnection(gobject.GObject):
    
    __gsignals__ = {
        "closed" : (gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    tuple()),
    }
    
    def __init__(self, app):
        self.app = app
        self.datasource_info = None
        self.conn_number = None
        self.threadsafety = 0
        self.__gobject_init__()
        
    def get_label(self):
        return self.datasource_info.get_label() + " #%s" % self.conn_number
        
    def close(self):
        self.emit("closed")
        
    def cursor(self):
        raise NotImplementedError
    
class DBCursor(gobject.GObject):
    
    def __init__(self, connection):
        self.connection = connection
        self.__gobject_init__()
        
    def execute(self, query):
        raise NotImplementedError
    
    
class Query(gobject.GObject):
    
    __gsignals__ = {
        "started" : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     tuple()),
        "finished" : (gobject.SIGNAL_RUN_LAST,
                      gobject.TYPE_NONE,
                      tuple())
    }
    
    def __init__(self, statement, cursor):
        self.__gobject_init__()
        self.statement = statement
        self.cursor = cursor
        self.description = None
        self.rowcount = -1
        self.rows = None
        self.messages = None
        self.failed = False
        self.executed = False
        self.execution_time = None
        self.errors = list()
        
    def execute(self, threaded=False):
        self.emit("started")
        try:
            self.cursor.execute(self.statement)
        except:
            self.failed = True
            self.errors.append(str(sys.exc_info()[1]))
        self.executed = True
        if not self.failed:
            self.description = self.cursor.description
            self.rowcount = self.cursor.rowcount
            if self.description:
                self.rows = self.cursor.fetchall()
        self.emit("finished")