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

"""Django Backend
"""

import gtk

from cf.plugins.core import DBBackendPlugin, PLUGIN_TYPE_BACKEND
from cf.backends import DBConnection, DBCursor, DBConnectError
from cf.datasources import DatasourceInfo
from cf.plugins.mixins import MenubarMixin, EditorMixin
from cf.ui.widgets import CustomImageMenuItem
from cf.backends.schema import *

import os
import sys
import md5
from gettext import gettext as _

import logging
log = logging.getLogger("DJANGO")


class DjangoBackendPlugin(DBBackendPlugin):
    id = "crunchyfrog.backend.django"
    plugin_type = PLUGIN_TYPE_BACKEND
    name = "Django Backend"
    description = "Provides access to models in a Django project"
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://cf.andialbrecht.de"
    version = "0.1"
    
    def __init__(self, *args, **kw):
        DBBackendPlugin.__init__(self, *args, **kw)
        self.schema = DjangoSchema()
        
    @classmethod
    def _get_filename(cls, chooser):
        return chooser.get_filename()
        
    def shutdown(self):
        log.info("Shutting down Django backend")
    
    @classmethod
    def get_datasource_options_widgets(cls, data_widgets, initial_data=None):
        lbl = gtk.Label(_(u"Settings file:"))
        lbl.set_alignment(0, 0.5)
        file_chooser = gtk.FileChooserButton(_(u"Select Django settings file"))
        filter = gtk.FileFilter()
        filter.set_name("Django settings")
        filter.add_pattern("settings.py")
        file_chooser.add_filter(filter)
        file_chooser.set_filter(filter)
        if initial_data:
            file_chooser.select_filename(initial_data.options.get("settings_file"))
        data_widgets["settings_file"] = (cls._get_filename, file_chooser)
        return data_widgets, [lbl, file_chooser]
    
    @classmethod
    def get_label(cls, datasource_info):
        return "%s (django://%s)" % (datasource_info.name, datasource_info.options.get("settings_file"))
    
    def dbconnect(self, data):
        try:
            import django
        except ImportError:
            raise DBConnectError(_(u"Python module django is not installed."))
        return DjangoConnection(self, self.app, data)
    
    def test_connection(self, data):
        try:
            conn = self.dbconnect(data)
            conn.close()
        except DBConnectError, err:
            return str(err)
        return None
    
class DjangoCursor(DBCursor):
    
    def __init__(self, connection):
        DBCursor.__init__(self, connection)
        self._cur = self.connection._conn.cursor()
        
    def _get_description(self):
        return self._cur.cursor.description
    description = property(fget=_get_description)
    
    def _get_rowcount(self):
        return self._cur.cursor.rowcount
    rowcount = property(fget=_get_rowcount)
        
    def execute(self, statement):
        try:
            self._cur.execute(statement)
            exc = None
        except:
            exc = sys.exc_info()
        self.connection.update_transaction_status()
        if exc:
            raise exc[1]
        
    def fetchall(self):
        return self._cur.cursor.fetchall()
    
    def close(self):
        self._cur.cursor.close()
    
class DjangoConnection(DBConnection):
    
    cursor_class = DjangoCursor
    
    def __init__(self, provider, app, data):
        DBConnection.__init__(self, provider, app)
        self.data = data
        self.settings_file = data["settings_file"]
        self.settings_path = os.path.dirname(self.settings_file)
        self.app_name = os.path.basename(self.settings_path)
        self.settings_env = "CF_DJANGO_%s" % md5.new(self.settings_file).hexdigest()
        sys.path.insert(0, os.path.abspath(os.path.join(self.settings_path, "../")))
        os.environ[self.settings_env] = "%s.settings" % (self.app_name)
        from django import conf
        conf.ENVIRONMENT_VARIABLE = self.settings_env
        from django.conf import settings
        self.settings = settings
        from django.db import connection
        self._conn = connection
        
    def close(self):
        self._conn.close()
        DBConnection.close(self)
        
    def cursor(self):
        return self.cursor_class(self)
    
    def commit(self):
        self._conn._commit()
        self.update_transaction_status()
        
    def rollback(self):
        self._conn._rollback()
        self.update_transaction_status()
        
    def explain(self, statement):
        try:
            sql = "EXPLAIN %s" % statement
            cur = self._conn.cursor()
            cur.execute(sql)
            data = cur.fetchall()
            cur.close()
        except:
            gtk.gdk.threads_enter()
            dialogs.error(_(u"An error occured"), str(sys.exc_info()[1]))
            gtk.gdk.threads_leave()
            return []
        return data
        
class DjApp(Node):
    icon = "gtk-open"
    
class DjModel(Table):
    pass
    
class DjModelField(Column):
    pass
        
class DjangoSchema(SchemaProvider):
    
    def __init__(self):
        SchemaProvider.__init__(self)
        
    def fetch_children(self, connection, parent):
        from django.db import models
        if isinstance(parent, DatasourceInfo):
            return [DjApp(app.__name__.split('.')[-2],
                          _(u"Module: %s") % app.__name__,
                          app=app) for app in models.get_apps()]
        elif isinstance(parent, DjApp):
            return [DjModel(model._meta.object_name,
                            _(u"Table: %s") % model._meta.db_table,
                            model=model) for model in models.get_models(parent.get_data("app"))]
        elif isinstance(parent, DjModel):
            return [DjModelField(field.name,
                                 _(u"Column: %s (%s)") % (field.get_attname(),
                                                          field.db_type()),
                                 field=field)
                    for field in parent.get_data("model")._meta.fields]