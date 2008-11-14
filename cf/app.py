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

"""Application object

"""

import os
import sys
import threading

import gobject
import gtk

from cf import release, USER_DIR
from config import Config
from datasources import DatasourceManager
from plugins.core import PluginManager
from ui.prefs import PreferencesDialog
from cf.userdb import UserDB
from ipc import IPCListener

import logging


class CFApplication(gobject.GObject):
    """Main application object.

    An instance of this class is accessible in almost every class in
    CrunchyFrog through the ``app`` attribute. It provides access
    to application internals.

    The easiest way to learn more about this object is to activate the
    Python shell plugin. The shell has two local variables: ``app``
    is the CFApplication instance and ``instance`` is the `CFInstance`_
    object for the GUI the shell runs in.

    Attributes
    ==========

        :config: Configuration (see `Config`_ class)
        :userdb: User database (see `UserDB`_ class)
        :plugins: Plugin registry (see `PluginManager`_ class)
        :datasources: Datasource information (see `DatasourceManager`_ class)

    .. _Config: cf.config.Config.html
    .. _UserDB: cf.userdb.UserDB.html
    .. _PluginManager: cf.plugins.core.PluginManager.html
    .. _DatasourceManager: cf.datasources.DatasourceManager.html
    .. _CFInstance: cf.instance.CFInstance.html
    """

    def __init__(self, options):
        """
        The constructor of this class takes one argument:

        :Parameter:
            options
                Commandline options as returned by `optparse`_

        .. _optparse: http://docs.python.org/lib/module-optparse.html
        """
        self.__gobject_init__()
        self.set_data("instances", {})
        self.__icount = 0L
        self.options = options

    def init(self):
        """Initializes the application"""
        self.cb = CFAppCallbacks()
        self.__shutdown_tasks = []
        self._check_version()
        self.config = Config(self, self.options.config)
        self.userdb = UserDB(self)
        self.run_listener()
        self.plugins = PluginManager(self)
        self.datasources = DatasourceManager(self)
        self.recent_manager = gtk.recent_manager_get_default()

    def _check_version(self):
        """Run eventual version updates."""
        version_file = os.path.join(USER_DIR, 'VERSION')
        if not os.path.isfile(version_file):
            f = open(version_file, "w")
            f.write("0.3.0")
            f.close()
        # That's it for now, it's for future use.

    def new_instance(self, args=None):
        """Creates a new instances.

        ``args`` is an optional list of file names to open
        """
        from cf.instance import CFInstance
        instance = CFInstance(self)
        instances = self.get_data("instances")
        self.__icount += 1
        instances[self.__icount] = instance
        self.set_data("instances", instances)
        instance.set_data("instance-id", self.__icount)
        instance.widget.connect("destroy",
                                self.on_instance_destroyed, self.__icount)
        instance.widget.show()
        self.cb.emit("instance-created", instance)
        return instance

    def on_instance_destroyed(self, instance, instance_id):
        instances = self.get_data("instances")
        if instances.has_key(instance_id):
            del instances[instance_id]
        self.set_data("instances", instances)
        if not instances:
            self.shutdown()

    def get_instance(self, instance_id):
        """Returns an instances identified by ID"""
        return self.get_data("instances").get(instance_id)

    def get_instances(self):
        """Returns a list of active instances

        :Returns: List of `CFInstance`_ instances

        .. _CFInstance: cf.instance.CFInstance.html
        """
        return self.get_data("instances").values()

    def preferences_show(self, mode="editor"):
        """Displays the preferences dialog"""
        dlg = PreferencesDialog(self, mode=mode)
        dlg.run() # IGNORE:E1101 - Generic method
        dlg.destroy() # IGNORE:E1101 - Generic method

    def register_shutdown_task(self, func, msg, *args, **kwargs):
        """Registers a new shutdown task.

        Shutdown tasks are executed when the ``shutdown`` method is
        called.

        :Parameter:
            func
                A callable
            msg
                A human readable message explaingin what the task does
            args, kwargs
                arguments and keyword arguments for ``func`` (optional)
        """
        self.__shutdown_tasks.append((func, msg, args, kwargs))

    def run_listener(self):
        """Creates and runs a simple socket server."""
        self.ipc_listener = IPCListener(self)
        t = threading.Thread(target=self.ipc_listener.serve_forever)
        t.setDaemon(True)
        t.start()

    def shutdown(self):
        """Execute all shutdown tasks and quit application

        Shutdown tasks are called within a try-except-block. If an
        exception is raised it will be printed to stdout.
        """
        while self.__shutdown_tasks:
            func, msg, args, kwargs = self.__shutdown_tasks.pop()
            logging.info(msg)
            try:
                func(*args, **kwargs)
            except:
                import traceback; traceback.print_exc()
                logging.error("Task failed: %s" % str(sys.exc_info()[1]))
        self.ipc_listener.shutdown()
        gtk.main_quit()


class CFAppCallbacks(gobject.GObject):
    """Container for application specific signals.

    Signals
    =======

        instance-created
            ``def callback(application, instance, user_data1, ...)``

            Called when a new instance was created
    """

    __gsignals__ = {
        "instance-created" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT,)),
    }
