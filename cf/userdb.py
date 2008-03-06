# -*- coding: utf-8 -*-

# crunchyfrog - a database schema browser and query tool
# Copyright (C) 2007 Andi Albrecht <albrecht.andi@gmail.com>
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

"""User database

The user database can be used by plugins to store some information.
It is also used by CrunchyFrog itself i.e. to store connection data.

:USER_DB: Path to sqlite3 file
"""

import gobject

import os.path
try:
    import sqlite3 as sqlite
except ImportError:
    from pysqlite2 import dbapi2 as sqlite

from cf import USER_DIR

USER_DB = os.path.join(USER_DIR, "user.db")

import logging
log = logging.getLogger("USERDB")

class UserDB(gobject.GObject):
    """User database class.
    
    An instance of this class is accessible through the ``userdb``
    attribute of an `CFApplication`_ instance.
    
    Usage example
    =============
    
        .. sourcecode:: python
        
            >>> app.userdb.get_table_version("foo")
            None
            >>> app.userdb.create_table("foo", "0.1", create_statement)
            >>> app.userdb.get_table_version("foo")
            '0.1'
            >>> app.userdb.cursor.execute("insert into foo (value) values (?)", ("bar",))
            >>> app.userdb.conn.commit()
            >>> app.userdb.cursor.execute("select * from foo")
            >>> app.userdb.cursor.fetchone()
            ('bar',)
            >>> app.userdb.drop_table("foo")
    
    
    Instance attributes
    ===================
    
        :conn: Database connection (sqlite connection)
        :cursor: Database cursor (sqlite cursor)
    
    
    .. _CFApplication: cf.app.CFApplication.html
    """
    
    def __init__(self, app):
        """
        :Parameters:
            app
                `CFApplication` instance
        """
        self.app = app
        self.conn = None
        self._user_db = self.app.config.get("userdb.file", USER_DB)
        self.__gobject_init__()
        self.__init_userdb()
        
    def _get_connection(self):
        return self.conn
    connection = property(fget=_get_connection)
        
    def __init_userdb(self):
        """Initializes the connection and cursor.
        
        This method creates the database if necessary.
        """
        log.debug("Initializing user database")
        create = not os.path.isfile(self._user_db)
        self.conn = sqlite.connect(self._user_db)
        self.cursor = self.conn.cursor()
        if create:
            self.__create_userdb()
        
    def __create_userdb(self):
        """Creates the sqlite3 file and some core tables."""
        sql = "create table sy_table_version (id integer primary key, \
        tablename text, version text)"
        self.cursor.execute(sql)
        from cf import datasources
        datasources.check_userdb(self)
        
    def get_cursor(self):
        """Returns a new DB-API compliant cursor.
        
        :Returns: DB-API compliant cursor
        """
        return self.conn.cursor()
    
    def get_table_version(self, table_name):
        """Returns the version of a table or ``None``.
        
        ``None`` is returned, if the table isn't registered
        with the `create_table` method, that means, if it's not
        found in ``sy_table_version``.
        
        :Parameter:
            table_name
                Name of the table
        
        :Returns: Version of the table, or ``None``
        """
        sql = "select version from sy_table_version \
        where tablename=?"
        try:
            self.cursor.execute(sql, (table_name,))
        except sqlite.OperationalError, e:
            log.warning("sy_table_version not found: %s" % str(e))
            return None
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            return None
    
    def create_table(self, name, version, statement):
        """Creates and registers a table.
        
        :Parameter:
            name
                Table name
            version
                Table version
            statement
                ``CREATE`` statement to create the table
                
        :Returns: ``True`` if the table was successfully created, otherwise ``False``
        """
        if self.get_table_version(name):
            log.error("Table '%s' already exists.", name)
            return False
        try:
            self.cursor.execute(statement)
        except sqlite.OperationalError, e:
            log.error("Failed to create table '%s': %s", name, str(e))
            return False
        sql = "insert into sy_table_version (tablename, version) \
        values (?,?)"
        self.cursor.execute(sql, (name, version))
        self.conn.commit()
        return True
    
    def drop_table(self, name):
        """Deletes and unregisters a table.
        
        :Parameter:
            name
                Table name
                
        :Returns: ``True`` if the table was successfully dropped, otherwise ``False``
        """
        sql = "delete from sy_table_version where tablename=?"
        self.cursor.execute(sql, (name,))
        self.conn.commit()
        sql = "drop table %s" % name
        try:
            self.cursor.execute(sql)
        except sqlite.OperationalError, e:
            log.error("Failed to delete table: %s", str(e))
            return False
        return True
        
        