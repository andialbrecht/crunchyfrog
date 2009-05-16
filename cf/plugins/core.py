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

"""Core objects"""

import gobject
import sys
import os
from inspect import isclass
import imp
import zipimport

try:
    import gnomevfs
    HAVE_GNOMEVFS = True
except ImportError:
    HAVE_GNOMEVFS = False

import logging
log = logging.getLogger("PLUGINS")

from gettext import gettext as _

PLUGIN_TYPE_GENERIC = 0
PLUGIN_TYPE_EXPORT = 2
PLUGIN_TYPE_EDITOR = 3

from cf import USER_PLUGIN_DIR, PLUGIN_DIR

from cf.plugins.mixins import InstanceMixin, MenubarMixin, EditorMixin
from cf.plugins.mixins import UserDBMixin
from cf.ui import dialogs


class GenericPlugin(gobject.GObject):
    """Plugin base class"""

    id = None
    name = None
    description = None
    long_description = None
    icon = None
    author = None
    license = None
    homepage = None
    version = None
    has_custom_options = False
    plugin_type = PLUGIN_TYPE_GENERIC
    INIT_ERROR = None

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


class BottomPanePlugin(GenericPlugin):
    """A plugin that lives in the bottom pane."""

class ExportPlugin(GenericPlugin):
    """Export filter base class"""
    icon = "gtk-save-as"
    file_filter_name = None
    file_filter_mime = []
    file_filter_pattern = []
    has_options = False
    plugin_type = PLUGIN_TYPE_EXPORT

    def __init__(self, app):
        GenericPlugin.__init__(self, app)

    def export(self, description, rows, options=dict()):
        raise NotImplementedError

    def show_options(self, description, rows):
        return dict()


# Key: plugin type
# Value: 2-tuple (label, expected class)
PLUGIN_TYPES_MAP = {
    PLUGIN_TYPE_GENERIC : (_(u"Miscellaneous"), GenericPlugin),
    PLUGIN_TYPE_EXPORT : (_(u"Export filter"), ExportPlugin),
    PLUGIN_TYPE_EDITOR : (_(u"Editor"), GenericPlugin),
}

class PluginManager(gobject.GObject):
    """Plugin manager

    An instance of this class is accessible through the ``plugins``
    attribute of an `CFApplication`_ instance.

    :Signals:

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

    plugin_types = PLUGIN_TYPES_MAP

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
        if HAVE_GNOMEVFS:
            gnomevfs.monitor_add(USER_PLUGIN_DIR,
                                 gnomevfs.MONITOR_DIRECTORY,
                                 self.on_plugin_folder_changed)
            gnomevfs.monitor_add(PLUGIN_DIR,
                                 gnomevfs.MONITOR_DIRECTORY,
                                 self.on_plugin_folder_changed)
        self.app.register_shutdown_task(self.on_app_shutdown, "")
        self.app.cb.connect("instance-created", self.on_instance_created)
        self.refresh()
        self._first_run()

    def on_app_shutdown(self):
        for plugin in self.__active_plugins.values():
            plugin.shutdown()

    def on_instance_created(self, cb, instance):
        for plugin in self.__active_plugins.values():
            if isinstance(plugin, InstanceMixin):
                self.init_instance_mixins(plugin, instance)

    def on_plugin_folder_changed(self, folder, path, change):
        if HAVE_GNOMEVFS and change in [gnomevfs.MONITOR_EVENT_DELETED,
                                        gnomevfs.MONITOR_EVENT_CREATED]:
            gobject.idle_add(self.refresh)

    def _first_run(self):
        if not self.app.options.first_run:
            return

    def get_plugins(self, plugin_type, active_only=False):
        """Returns a list of plugins.

        :Parameter:
            plugin_type
                a ``PLUGIN_TYPE_*`` constant

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
            if item.plugin_type == plugin_type:
                ret.append(item)
        return ret

    def _get_modules(self, path):
        modules = []
        if not os.access(path, os.R_OK) or not os.path.exists(path):
            logging.warning('Plugin path %s missing', path)
            return modules
        if path not in sys.path:
            sys.path.insert(0, path)
        for item in os.listdir(path):
            if item.startswith(".") or item.startswith("_"):
                continue
            name, ext = os.path.splitext(item)
            if ext and ext not in [".zip", ".py"]:
                continue
            elif not ext and not os.path.isfile(os.path.join(path, item,
                                                             '__init__.py')):
                continue
            if ext == ".zip":
                sys.path.insert(0, os.path.join(path, item))
                importer = zipimport.zipimporter(os.path.join(path, item))
                importer = importer.find_module(name)
                if not importer:
                    continue
                mod = importer.load_module(name)
                modules.append(mod)
            else:
                try:
                    modinfo = imp.find_module(name)
                except ImportError, err:
                    logging.error('Failed to load module %s: %s', name, err)
                    continue
                try:
                    mod = imp.load_module(name, *modinfo)
                except Exception, err:
                    logging.error('Failed to load module %s: %s', name, err)
                    try: del sys.modules[name]
                    except KeyError: pass
                    continue
                modules.append(mod)
        return modules

    def _get_plugins(self, module):
        plugins = []
        for name in dir(module):
            obj = getattr(module, name)
            if isclass(obj) and issubclass(obj, GenericPlugin) \
            and obj not in [GenericPlugin, ExportPlugin]:
                plugins.append(obj)
        return plugins

    def refresh(self):
        """Refreshs the plugin registry.

        This method is called when the contents of a plugin folder
        changes.
        """
        from cf.plugins import builtin
        modules = [builtin]
        for path in [PLUGIN_DIR, USER_PLUGIN_DIR]:
            modules += self._get_modules(path)
        plugins = []
        for module in modules:
            plugins += self._get_plugins(module)
        ids_found = []
        for plugin in plugins:
            if not self.__plugins.has_key(plugin.id):
                self.__plugins[plugin.id] = plugin
                l = self.app.config.get("plugins.active", [])
                if plugin.id in l and not plugin.INIT_ERROR:
                    self.set_active(plugin, True)
                elif plugin.id in l and plugin.INIT_ERROR:
                    self.set_active(plugin, False)
                self.emit("plugin-added", plugin)
            ids_found.append(plugin.id)
        for id, plugin in self.__plugins.items():
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
                for instance in self.app.get_instances():
                    self.init_instance_mixins(x, instance)
            if id not in l:
                l.append(id)
        elif not active:
            x = self.__active_plugins.get(plugin, None)
            if x:
                if isinstance(x, InstanceMixin):
                    for instance in self.app.get_instances():
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
        plugins = self.__active_plugins.values()
        if not active_only:
            plugins += self.__plugins.values()
        for plugin in plugins:
            if plugin.id == id:
                return plugin
        return None

    def init_instance_mixins(self, plugin, instance):
        plugin.init_instance(instance)

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

