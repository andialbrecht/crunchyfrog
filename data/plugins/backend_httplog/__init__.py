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

# For the apachelogs module:
#   (c) Kevin Scott (kevin.scott@gmail.com)
#   modified by bkjones for the Loghetti project (http://code.google.com/p/loghetti/)

# $Id$

"""Backend for http server (Apache, Lighttpd) log files

This backend can be used for simple log file analysis of
HTTP logs in combined format.
"""

import gtk

from cf.plugins.core import DBBackendPlugin, PLUGIN_TYPE_BACKEND
from cf.backends import DBConnectError
from cf.backends.dbapi2helper import DbAPI2Connection
from cf.datasources import DatasourceInfo
from cf.plugins.mixins import MenubarMixin, EditorMixin
from cf.ui.widgets import CustomImageMenuItem
from cf.backends.schema import *

import os
import sys
import md5
from gettext import gettext as _
from tempfile import mkstemp

import logging
log = logging.getLogger("HTTP-LOG")

import apachelogs

class HttpLogBackendPlugin(DBBackendPlugin):
    id = "crunchyfrog.backend.http"
    plugin_type = PLUGIN_TYPE_BACKEND
    name = "HTTP log file backend"
    description = "Analyse HTTP log files with SQL"
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://cf.andialbrecht.de"
    version = "0.1"
    
    def __init__(self, *args, **kw):
        DBBackendPlugin.__init__(self, *args, **kw)
        self.db_file = None
        
    @classmethod
    def _get_filename(cls, chooser):
        return chooser.get_filename()
        
    def shutdown(self):
        log.info("Shutting down HTTP log backend")
        if self.db_file and os.path.isfile(self.db_file):
            os.remove(self.db_file)
    
    @classmethod
    def get_datasource_options_widgets(cls, data_widgets, initial_data=None):
        lbl = gtk.Label(_(u"Log file:"))
        lbl.set_alignment(0, 0.5)
        file_chooser = gtk.FileChooserButton(_(u"Select HTTP log file"))
        if initial_data:
            file_chooser.select_filename(initial_data.options.get("log_file"))
        data_widgets["log_file"] = (cls._get_filename, file_chooser)
        return data_widgets, [lbl, file_chooser]
    
    @classmethod
    def get_label(cls, datasource_info):
        return "%s (http-log://%s)" % (datasource_info.name, datasource_info.options.get("log_file"))
    
    def dbconnect(self, data):
        create_db = False
        if not self.db_file:
            create_db = True
            fd, self.db_file = mkstemp(".db", "cf-http-log-")
        try:
            import sqlite3
            if create_db:
                self.init_db(self.db_file, data["log_file"])
            real_conn = sqlite3.connect(self.db_file)
            return HttpLogConnection(self, self.app, real_conn, data["log_file"])
        except StandardError, err:
            raise DBConnectError(str(err))
    
    def test_connection(self, data):
        try:
            conn = self.dbconnect(data)
            conn.close()
        except DBConnectError, err:
            return str(err)
        return None
    
    def init_db(self, dbfile, logfile):
        conn = sqlite3.connect(dbfile)
        cur = conn.cursor()
        cur.execute(TABLE_CREATE)
        print logfile
        lf = apachelogs.ApacheLogFile(logfile)
        for line in lf:
            data = dict()
            for name in dir(line):
                if name.startswith("__"):
                    continue
                data[name] = getattr(line, name)
                if name.startswith("http_response"):
                    data[name] = int(data[name])
            sql = SQL_INSERT % data
            cur.execute(sql)
        conn.commit()
    
class HttpLogConnection(DbAPI2Connection):
    
    def __init__(self, backend, app, real_conn, log_file):
        DbAPI2Connection.__init__(self, backend, app, real_conn)
        self.log_file = log_file
    
    def get_server_info(self):
        return self.log_file
    
    
TABLE_CREATE = """
create table logfile (
    http_method text,
    http_response_code integer,
    http_response_size integer,
    http_user text,
    http_vers text,
    ident text,
    ip text,
    referrer text,
    request_line text,
    time text,
    url text,
    user_agent text
);
"""
SQL_INSERT = """
INSERT INTO log (http_method, http_response_code, http_response_size,
http_user, http_vers, referrer, request_line, time, url, user_agent,
ident, ip)
values ('%(http_method)s', %(http_response_code)d, %(http_response_size)d,
'%(http_user)s', '%(http_vers)s', '%(referrer)s', '%(request_line)s', 
'%(time)s', '%(url)s', '%(user_agent)s', '%(ident)s', '%(ip)s')
"""


try:
    import sqlite3
except ImportError:
    HttpLogBackendPlugin.INIT_ERROR = _(u"Python module sqlite3 required.")