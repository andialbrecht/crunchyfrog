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

"""Application object"""

import logging
import os
import sys
import threading
import urlparse
import webbrowser

import gobject
import gtk

from cf import release, USER_DIR, MANUAL_URL
from config import Config
from datasources import DatasourceManager
from plugins.core import PluginManager
from cf.ui.widgets import ConnectionsDialog
from ui.mainwindow import MainWindow
from ui.prefs import PreferencesDialog
from cf.userdb import UserDB

import logging


class CFApplication(gobject.GObject):
    """Main application object.

    An instance of this class is accessible in almost every class in
    CrunchyFrog through the app attribute. It provides access
    to application internals.

    Instance attributes:
      config: Configuration
      userdb: User database
      plugins: Plugin registry
      datasources: Datasource information
    """

    def __init__(self, options):
        """Constructor.

        Parameter:
          options: Command line options as returned by optparse.
        """
        self.__gobject_init__()
        self._instances = []
        self.__icount = 0
        self.options = options
        self.icon_theme = gtk.icon_theme_get_default()

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
        """Run possible version updates."""
        version_file = os.path.join(USER_DIR, 'VERSION')
        if not os.path.isfile(version_file):
            f = open(version_file, "w")
            f.write("0.3.0")
            f.close()
        # That's it for now, it's for future use.

    # ---
    # Instance handling
    # ---

    def new_instance(self, args=None, show=True):
        """Creates a new instances.

        Arguments:
          args: List of filenames to open in new instance (default: None).
          show: If True, instance.show() is called here (default: True).

        Returns:
          The new instance.
        """
        instance = MainWindow(self)
        if args is None:
            args = []
        for arg in args:
            instance.editor_create(arg)
        self._instances.append(instance)
        instance.connect("destroy", self.on_instance_destroyed)
        if show:
            instance.show()
        self.cb.emit("instance-created", instance)
        return instance

    def on_instance_destroyed(self, instance):
        instances = self.get_data("instances")
        if instance in self._instances:
            self._instances.remove(instance)
        if len(self._instances) == 0:
            self.shutdown()

    def get_instance(self, instance_id):
        """Returns an instances identified by ID."""
        for instance in self._instances:
            if id(instance) == instance_id:
                return instance

    def get_instances(self):
        """Returns a list of active instances."""
        return self._instances

    # ---

    def manage_connections(self, win):
        """Displays a dialog to manage connections."""
        dlg = ConnectionsDialog(win)
        dlg.run()
        dlg.destroy()

    def preferences_show(self, win, mode="editor"):
        """Displays the preferences dialog"""
        dlg = PreferencesDialog(win, mode=mode)
        dlg.run() # IGNORE:E1101 - Generic method
        dlg.destroy() # IGNORE:E1101 - Generic method

    def register_shutdown_task(self, func, msg, *args, **kwargs):
        """Registers a new shutdown task.

        Shutdown tasks are executed when the shutdown method is
        called.

        Parameter:
          func: A callable to execute.
          msg:  A human readable message explaining what the task does.
          args, kwargs: arguments and keyword arguments for func (optional).
        """
        self.__shutdown_tasks.append((func, msg, args, kwargs))

    def run_listener(self):
        """Creates and runs a simple socket server."""
        try:
            from cf.ipc import IPCListener
        except AttributeError:
            self.ipc_listener = None
            return
        self.ipc_listener = IPCListener(self)
        t = threading.Thread(target=self.ipc_listener.serve_forever)
        t.setDaemon(True)
        t.start()

    def show_help(self, topic=None):
        """Opens a webbrowser with a help page.

        Arguments:
          topic: If given, the URL points to the selected topic.
        """
        if topic is None:
            url = os.path.join(MANUAL_URL, 'index.html')
        webbrowser.open(url)

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
        if self.ipc_listener is not None:
            self.ipc_listener.shutdown()
        gtk.main_quit()

    def load_icon(self, icon_name, size=None, lookup_method=None):
        """Wrapper for gtk.IconTheme.load_icon that catches GError."""
        if size is None:
            size = gtk.ICON_SIZE_MENU
        if lookup_method is None:
            lookup_method = (gtk.ICON_LOOKUP_FORCE_SVG |
                             gtk.ICON_LOOKUP_USE_BUILTIN |
                             gtk.ICON_LOOKUP_GENERIC_FALLBACK)
        try:
            return self.icon_theme.load_icon(icon_name, size, lookup_method)
        except gobject.GError, err:
            logging.warning(err)
            return self.icon_theme.load_icon('gtk-missing-image',
                                             size, lookup_method)


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
