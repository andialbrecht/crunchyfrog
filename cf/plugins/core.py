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

"""Core objects"""

import gobject
import gnomevfs
import pkg_resources
import sys
import os
from kiwi.ui import dialogs

import logging
log = logging.getLogger("PLUGINS")

from gettext import gettext as _

from cf import USER_PLUGIN_DIR, PLUGIN_DIR

class GenericPlugin(gobject.GObject):
    
    name = None
    description = None
    long_description = None
    icon = None
    author = None
    license = None
    homepage = None
    version = None
    
    def __init__(self, app):
        self.app = app
        self.__gobject_init__()
        
    def shutdown(self):
        pass
        
class DBBackendPlugin(GenericPlugin):
    icon = "stock_database"
    
    def __init__(self, app):
        GenericPlugin.__init__(self, app)
        self.schema = None
    
    @classmethod
    def get_datasource_options_widgets(cls, data_widgets, initial_data=None):
        return data_widgets, []
    # TODO: Documentation
    
    @classmethod
    def get_label(cls, datasource_info):
        s = "%s@%s on %s" % (datasource_info.options.get("user", None) or "??",
                             datasource_info.options.get("database", None) or "??",
                             datasource_info.options.get("host", None) or "??")
        if datasource_info.name:
            s = '%s (%s)' % (datasource_info.name, s)
        return s
    
    def test_connection(self, data):
        raise NotImplementedError
    
    def password_prompt(self):
        return dialogs.password(_(u"Password required"), _(u"Enter the password to connect to this database."))
        
# Available entry points
# Key: entry point name
# Value: 2-tuple (label, expected class)
ENTRY_POINTS = {
    "crunchyfrog.plugin" : (_(u"Miscellaneous"), GenericPlugin),
    "crunchyfrog.backend" : (_(u"Database backends"), DBBackendPlugin),
} 

class PluginManager(gobject.GObject):
    """Plugin manager"""
    
    entry_points = ENTRY_POINTS
    
    __gsignals__ = {
        "plugin-added" : (gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          (gobject.TYPE_PYOBJECT,)),
        "plugin-removed" : (gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            (gobject.TYPE_PYOBJECT,)),
        "plugin-active" : (gobject.SIGNAL_RUN_LAST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_PYOBJECT, bool)),
    }
    
    def __init__(self, app):
        self.app = app
        self.__gobject_init__()
        self.__plugins = dict()
        self.__active_plugins = dict()
        gnomevfs.monitor_add(USER_PLUGIN_DIR, gnomevfs.MONITOR_DIRECTORY, self.on_plugin_folder_changed)
        gnomevfs.monitor_add(PLUGIN_DIR, gnomevfs.MONITOR_DIRECTORY, self.on_plugin_folder_changed)
        self.refresh()
        
    def on_plugin_folder_changed(self, folder, path, change):
        if change in [gnomevfs.MONITOR_EVENT_DELETED, gnomevfs.MONITOR_EVENT_CREATED]:
            gobject.idle_add(self.refresh)
        
    def get_plugins(self, entry_point_name, active_only=False):
        ret = list()
        if active_only:
            plugins = self.__active_plugins.values()
        else:
            plugins = self.__plugins.values()
        for item in plugins:
            if item._entry_point_group == entry_point_name:
                ret.append(item)
        return ret
    
    def refresh(self):
        # cleanup sys.path to remove deleted eggs
        for path in sys.path:
            if path.endswith(".egg") and not os.path.isfile(path):
                sys.path.remove(path)
        working_set = pkg_resources.WorkingSet()
        working_set.add_entry(PLUGIN_DIR)
        working_set.add_entry(USER_PLUGIN_DIR)
        env = pkg_resources.Environment([PLUGIN_DIR, USER_PLUGIN_DIR])
        dists, errors = working_set.find_plugins(env)
        # TODO: Handle errors
        map(working_set.add, dists)
        for path in working_set.entries:
            if path not in sys.path:
                sys.path.append(path)
        dist = pkg_resources.get_distribution("crunchyfrog")
        ids_found = list()
        for entry_point_name in self.entry_points.keys():
            for entry_point in working_set.iter_entry_points(entry_point_name):
                id = ".".join([entry_point_name, entry_point.name])
                try:
                    plugin = entry_point.load()
                except:
                    import traceback; traceback.print_exc()
                    continue
                if not self.__plugins.has_key(id):
                    added = True
                else:
                    added = False
                plugin._entry_point = entry_point
                plugin._entry_point_group = entry_point_name
                plugin.id = ".".join([entry_point_name, entry_point.name])
                self.__plugins[id] = plugin
                ids_found.append(id)
                if added:
                    l = self.app.config.get("plugins.active", [])
                    if id in l:
                        self.set_active(plugin, True)
                    self.emit("plugin-added", plugin)
        for module_name, plugin in self.__plugins.items():
            entry_point = plugin._entry_point
            group = plugin._entry_point_group
            id = ".".join([group, entry_point.name])
            if id not in ids_found:
                l = self.app.config.get("plugins.active", [])
                if id in l:
                    self.set_active(plugin, False)
                del self.__plugins[id]
                self.emit("plugin-removed", plugin)
    
    def set_active(self, plugin, active):
        id = None
        for key, value in self.__plugins.items():
            if value == plugin:
                id = key
                break
        if not id: 
            return
        l = self.app.config.get("plugins.active", [])
        if active:
            x = plugin(self.app)
            self.__active_plugins[plugin] = x
            if id not in l:
                l.append(id)
        elif not active:
            x = self.__active_plugins.get(plugin, None)
            if x:
                x.shutdown()
                del self.__active_plugins[plugin]
            if id in l:
                l.remove(id)
        self.app.config.set("plugins.active", l)
        self.emit("plugin-active", plugin, active)
        
    def is_active(self, plugin):
        if isinstance(plugin, GenericPlugin):
            plugin = plugin.__class__
        return self.__active_plugins.has_key(plugin)
    
    def by_id(self, id, active_only=True):
        if active_only:
            plugins = self.__active_plugins.values()
        else:
            plugins = self.__plugins.values()
        for plugin in plugins:
            if plugin.id == id:
                return plugin
        return None