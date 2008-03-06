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

"""Database backends"""

__doc_all__ = ["schema",]

import gobject
import gtk

import sys
import time

from cf.utils import Emit

TRANSACTION_IDLE = 1 << 1
TRANSACTION_COMMIT_ENABLED = 1 << 2
TRANSACTION_ROLLBACK_ENABLED = 1 << 3


class DBError(StandardError):
    """Base class for database errors"""

class DBConnectError(DBError):
    """Errors on opening a connection"""
    
class DBConnection(gobject.GObject):
    
    __gsignals__ = {
        "closed" : (gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    tuple()),
        "notice" : (gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    (str,)),
    }
    
    __gproperties__ = {
        "transaction-state" : (gobject.TYPE_PYOBJECT,
                            "Transaction flag", "Transaction flag",
                            gobject.PARAM_READWRITE),
    }
    
    def __init__(self, provider, app):
        self.app = app
        self.provider = provider
        self.datasource_info = None
        self.conn_number = None
        self.threadsafety = 0
        self._transaction_state = TRANSACTION_IDLE
        self.__gobject_init__()
        
    def do_set_property(self, property, value):
        if property.name == "transaction-state":
            self._transaction_state = value
        else:
            raise AttributeError, "unknown property %r" % property.name
        
    def do_get_property(self, property):
        if property.name == "transaction-state":
            return self._transaction_state
        else:
            raise AttributeError, "unknown property %r" % property.name
        
    def get_label(self):
        return self.datasource_info.get_label() + " #%s" % self.conn_number
        
    def close(self):
        self.emit("closed")
        
    def cursor(self):
        raise NotImplementedError
    
    def update_transaction_status(self):
        pass
    
    def get_server_info(self):
        return None
    
    def commit(self):
        raise NotImplementedError
    
    def rollback(self):
        raise NotImplementedError
    
    def explain(self, statement):
        return []
    
class DBCursor(gobject.GObject):
    
    def __init__(self, connection):
        self.connection = connection
        self.__gobject_init__()
        
    def execute(self, query):
        raise NotImplementedError
    
    def get_messages(self):
        return []
    
    def close(self):
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
        start = time.time()
        if threaded:
            Emit(self, "started")
        else:
            self.emit("started")
        try:
            self.cursor.execute(self.statement)
        except:
            self.failed = True
            self.errors.append(str(sys.exc_info()[1]))
        self.executed = True
        self.execution_time = time.time() - start
        self.messages = self.cursor.get_messages()
        if not self.failed:
            self.description = self.cursor.description
            self.rowcount = self.cursor.rowcount
            if self.description:
                self.rows = self.cursor.fetchall()
        if threaded:
            Emit(self, "finished")
        else:
            self.emit("finished")
            
class ReferenceProvider(gobject.GObject):
    name = None
    base_url = None
    
    def __init__(self):
        self.__gobject_init__()
        
    def get_context_help_url(self, term):
        return None