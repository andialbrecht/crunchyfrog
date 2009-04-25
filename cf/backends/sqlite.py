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

"""SQLite3 backend"""

import gtk


from cf.backends import DBConnectError
from cf.backends.dbapi2helper import DbAPI2Connection, DbAPI2Cursor
from cf.backends.schema import *
from cf.plugins.core import DBBackendPlugin
from cf.datasources import DatasourceInfo

from gettext import gettext as _

import logging
log = logging.getLogger("SQLITE")

class SQLiteBackend(DBBackendPlugin):

    id = "crunchyfrog.backend.sqlite"
    name = _(u"SQLite3 Plugin")
    description = _(u"Provides access to SQLite3 databases")

    def __init__(self, app):
        DBBackendPlugin.__init__(self, app)
        log.info("Activating SQLite3 backend")
        self.schema = SQLiteSchema()
        self.features.transactions = True

    @classmethod
    def _get_filename(cls, chooser):
        return chooser.get_filename()

    def shutdown(self):
        log.info("Shutting down SQLite3 backend")

    @classmethod
    def get_datasource_options_widgets(cls, data_widgets, initial_data=None):
        lbl = gtk.Label(_(u"Database file:"))
        lbl.set_alignment(0, 0.5)
        file_chooser = gtk.FileChooserButton(_(u"Select database file"))
        if initial_data:
            file_chooser.select_filename(initial_data.options.get("filename"))
        data_widgets["filename"] = (cls._get_filename, file_chooser)
        return data_widgets, [lbl, file_chooser]

    @classmethod
    def get_label(cls, datasource_info):
        return "%s (sqlite://%s)" % (datasource_info.name, datasource_info.options.get("filename"))

    def dbconnect(self, data):
        try:
            import sqlite3
        except ImportError:
            raise DBConnectError(_(u"Python module sqlite3 is not installed."))
        try:
            real_conn = sqlite3.connect(data["filename"])
        except StandardError, err:
            raise DBConnectError(str(err))
        return SQLite3Connection(self, self.app, real_conn)

    def test_connection(self, data):
        try:
            conn = self.dbconnect(data)
            conn.close()
        except DBConnectError, err:
            return str(err)
        return None

class SQLite3Connection(DbAPI2Connection):

    def get_server_info(self):
        cur = self._conn.cursor()
        cur.execute("select sqlite_version()")
        ret = cur.fetchone()[0]
        cur.close()
        return "SQLite %s" % ret

class SQLiteSchema(SchemaProvider):

    def q(self, connection, sql):
        cur = connection.cursor()._cur
        cur.execute(sql)
        return cur.fetchall()

    def fetch_children(self, connection, parent):
        if isinstance(parent, DatasourceInfo):
            return [TableCollection(), ViewCollection()]

        elif isinstance(parent, TableCollection):
            ret = []
            sql = "select name from sqlite_master where type = 'table'"
            for item in self.q(connection, sql):
                ret.append(Table(item[0]))
            return ret

        elif isinstance(parent, ViewCollection):
            ret = []
            sql = "select name from sqlite_master where type = 'view'"
            for item in self.q(connection, sql):
                ret.append(View(item[0]))
            return ret

        elif isinstance(parent, Table) or isinstance(parent, View):
            return [ColumnCollection(table=parent)]

        elif isinstance(parent, ColumnCollection):
            ret = []
            sql = "pragma table_info('%s')" % parent.get_data("table").name
            return [Column(item[1]) for item in self.q(connection, sql)]


try:
    import sqlite3
except ImportError:
    SQLiteBackend.INIT_ERROR = _(u"Python module sqlite3 required.")
