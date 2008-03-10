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

from cf import USER_PLUGIN_DIR, PLUGIN_DIR, USER_PLUGIN_URI

from cf.plugins.mixins import InstanceMixin, MenubarMixin, EditorMixin
from cf.plugins.mixins import UserDBMixin
from cf.ui.widgets import ProgressDialog

class GenericPlugin(gobject.GObject):
    """Plugin base class"""
    
    name = None
    description = None
    long_description = None
    icon = None
    author = None
    license = None
    homepage = None
    version = None
    has_custom_options = False
    
    def __init__(self, app):
        """
        The constructor of this class takes one argument:
        
        :Parameter:
            app
                `CFApplication`_ instance
                
        .. _CFApplication: cf.app.CFApplication.html
        """
        self.app = app
        self.__gobject_init__()
        
    @classmethod
    def run_custom_options_dialog(cls, app):
        """Runs a preferences dialog
        
        If ``has_custom_options`` is ``True`` this method will
        be called if the user clicks on the *Configure plugin* button
        in the preferences dialog.
        
        :Parameter:
            app
                `CFApplication`_ instance
                
        .. _CFApplication: cf.app.CFApplication.html
        """
        pass
        
    def shutdown(self):
        """Called when the plugin is deactivated."""
        pass
    
class ExportPlugin(GenericPlugin):
    """Export filter base class"""
    icon = "gtk-save-as"
    file_filter_name = None
    file_filter_mime = []
    file_filter_pattern = []
    has_options = False
    
    def __init__(self, app):
        GenericPlugin.__init__(self, app)
        
    def export(self, description, rows, options=dict()):
        raise NotImplementedError
    
    def show_options(self, description, rows):
        return dict()
        
class DBBackendPlugin(GenericPlugin):
    """Database backend base class"""
    icon = "stock_database"
    context_help_pattern = None
    
    def __init__(self, app):
        GenericPlugin.__init__(self, app)
        self.schema = None
        self.reference = None
    
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
    "crunchyfrog.export": (_(u"Export filter"), ExportPlugin),
} 

class PluginManager(gobject.GObject):
    """Plugin manager
    
    An instance of this class is accessible through the ``plugins``
    attribute of an `CFApplication`_ instance.
    
    Signals
    =======
        
        plugin-added
            ``def callback(manager, plugin, user_param1, ...)``
            
            Emitted when a plugin was added to the registry.
            
        plugin-removed
            ``def callback(manager, plugin, user_param1, ...)``
            
            Emitted when a plugin is removed from the registry.
            
        plugin-active
            ``def callback(manager, plugin, active, user_param1, ...)``
            
            Emitted when a plugin is activated or deactivated. `active`
            is either ``True`` or ``False``.
    
    .. _CFApplication: cf.app.CFApplication.html
    """
    
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
        """
        The constructor of this class takes one argument:
        
        :Parameter:
            app
                `CFApplication`_ instance
                
        .. _CFApplication: cf.app.CFApplication.html
        """
        self.app = app
        self.__gobject_init__()
        self.__plugins = dict()
        self.__active_plugins = dict()
        gnomevfs.monitor_add(USER_PLUGIN_DIR, gnomevfs.MONITOR_DIRECTORY, self.on_plugin_folder_changed)
        gnomevfs.monitor_add(PLUGIN_DIR, gnomevfs.MONITOR_DIRECTORY, self.on_plugin_folder_changed)
        self.app.register_shutdown_task(self.on_app_shutdown, _(u"Closing plugins"))
        self.app.cb.connect("instance-created", self.on_instance_created)
        self.refresh()
        
    def on_app_shutdown(self):
        for plugin in self.__active_plugins.values():
            plugin.shutdown()
            
    def on_instance_created(self, cb, instance):
        for plugin in self.__active_plugins.values():
            if isinstance(plugin, InstanceMixin):
                self.init_instance_mixins(plugin, instance)
        
    def on_plugin_folder_changed(self, folder, path, change):
        if change in [gnomevfs.MONITOR_EVENT_DELETED, gnomevfs.MONITOR_EVENT_CREATED]:
            gobject.idle_add(self.refresh)
        
    def get_plugins(self, entry_point_name, active_only=False):
        """Returns a list of plugins.
        
        :Parameter:
            entry_point_name
                The name of an entry point. Must be a key of the ``ENTRY_POINTS``
                dictionary.
            
            active_only
                If set to ``True`` only activated plugins are returned.
                
        :Returns: 
            List of `plugins`_
        
        .. _plugins: cf.plugins.core.GenericPlugin.html
        """
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
        """Refreshs the plugin registry.
        
        This method is called when the contents of a plugin folder
        changes.
        """
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
    
    def set_active(self, plugin, active, instance=None):
        """Activates / deactivates a plugin
        
        :Parameter:
            plugin
                Plugin to activate / deactivate
            active
                If ``True`` the plugin gets activated, otherwise it will
                be deactivated.
        """
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
            if isinstance(x, UserDBMixin):
                x.userdb_set(self.app.userdb)
                x.userdb_init()
            if isinstance(x, InstanceMixin):
                for instance in self.app.get_data("instances") or []:
                    self.init_instance_mixins(x, instance)
            if id not in l:
                l.append(id)
        elif not active:
            x = self.__active_plugins.get(plugin, None)
            if x:
                if isinstance(x, InstanceMixin):
                    for instance in self.app.get_data("instances") or []:
                        self.unload_instance_mixins(x, instance)
                x.shutdown()
                del self.__active_plugins[plugin]
            if id in l:
                l.remove(id)
        self.app.config.set("plugins.active", l)
        self.emit("plugin-active", plugin, active)
        
    def is_active(self, plugin):
        """Returns ``True`` if the plugin is active
        
        :Parameter:
            plugin
                A plugin
                
        :Returns: ``True`` if the plugin is active.
        """
        if isinstance(plugin, GenericPlugin):
            plugin = plugin.__class__
        return self.__active_plugins.has_key(plugin)
    
    def by_id(self, id, active_only=True):
        """Returns a plugin by its id
        
        :Parameter:
            id
                Plugin ID
            active_only
                If ``True`` only active plugins are returned.
        
        :Returns: `Plugin`_ or ``None``
        
        .. _Plugin: cf.plugins.core.GenricPlugin.html
        """
        if active_only:
            plugins = self.__active_plugins.values()
        else:
            plugins = self.__plugins.values()
        for plugin in plugins:
            if plugin.id == id:
                return plugin
        return None
    
    def init_instance_mixins(self, plugin, instance):
        plugin.init_instance(instance)
        if isinstance(plugin, MenubarMixin):
            plugin.menubar_load(instance.xml.get_widget("menubar"), instance)
        if isinstance(plugin, EditorMixin):
            self.editor_notify(instance._editor, instance)
            
    def unload_instance_mixins(self, plugin, instance):
        if isinstance(plugin, MenubarMixin):
            plugin.menubar_unload(instance.xml.get_widget("menubar"), instance)
            
    def editor_notify(self, editor, instance):
        """Called by an instance when the current editor has changed
        
        :Parameter:
            editor
                an editor or ``None``
            instance
                an instance
        """
        for plugin in self.__active_plugins.values():
            if isinstance(plugin, EditorMixin):
                plugin.set_editor(editor, instance)
                
    def install_plugin(self, uri):
        """Installs a plugin from URI
        
        :Parameter:
            uri
                URI pointing to .egg file
        """
        def progress_cb(info, dlg):
            if info.bytes_total:
                fraction = info.total_bytes_copied/float(info.bytes_total)
            else:
                fraction = 0
            dlg.set_progress(fraction)
            return True
        source = gnomevfs.URI(uri)
        dest = gnomevfs.URI(USER_PLUGIN_URI).append_file_name(source.short_name)
        try:
            dlg = ProgressDialog(self.app)
            dlg.show_all()
            dlg.set_info(_(u"Copying files..."))
            gnomevfs.xfer_uri(source, dest, gnomevfs.XFER_DEFAULT,
                              gnomevfs.XFER_ERROR_MODE_QUERY,
                              gnomevfs.XFER_OVERWRITE_MODE_QUERY,
                              progress_cb, dlg)
            dlg.set_info(_(u"Plugin installed."))
        except:
            err = sys.exc_info()[1]
            dlg.set_error(err.message)
        dlg.set_finished(True)
            
            