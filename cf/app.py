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

"""Application object"""

import logging
import os
import sqlite3
import sys
import threading
import urlparse
import webbrowser

import gobject
import gtk

from cf import release, USER_DIR, MANUAL_URL, DATA_DIR, USER_CONFIG_DIR
from config import Config
from plugins.core import PluginManager
from cf.db import DatasourceManager
from cf.ui.datasources import DatasourcesDialog
from cf.ui.widgets import ConnectionsDialog
from ui.mainwindow import MainWindow
from ui.prefs import PreferencesDialog
from cf.userdb import UserDB
from cf import autocompletion

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
        self.config = Config(self, self.options.config)
        self.userdb = UserDB(self)
        self._check_version()
        self.run_listener()
        self.plugins = PluginManager(self)
        self.datasources = DatasourceManager(self)
        self.recent_manager = gtk.recent_manager_get_default()
        autocompletion.setup(self)

    def _check_version(self):
        """Run possible version updates."""
        version_file = os.path.join(USER_CONFIG_DIR, 'VERSION')
        if os.path.isfile(version_file):
            dir_version = open(version_file).read()
        else:
            # Upgrade to 0.4.0 regression
            version_file = os.path.expanduser('~/.crunchyfrog/VERSION')
            if os.path.isfile(version_file):
                dir_version = open(version_file).read()
            else:
                dir_version = None
            version_file = os.path.join(USER_CONFIG_DIR, 'VERSION')
        if dir_version is not None and dir_version != release.version:
            self._move_user_files(dir_version, release.version)
            self._datasources_db2url(dir_version, release.version)
            # Do upgrades here
            f = open(version_file, "w")
            f.write(release.version)
            f.close()

    def _move_user_files(self, dir_version, release):
        """Move user specific files and directories to new locations."""
        # Upgrade to 0.4.0: User specific files now life in proper locations
        #   following XDG Base Directory specification.
        import shutil
        import cf
        old_user_dir = os.path.expanduser('~/.crunchyfrog')
        logging.info('Migrating user dir %s', old_user_dir)
        if not os.path.exists(old_user_dir):
            return
        for fname in ['user.db', 'VERSION']:
            path = os.path.join(old_user_dir, fname)
            if not os.path.exists(path):
                continue
            shutil.move(path,
                        os.path.join(cf.USER_CONFIG_DIR, fname))
        if os.path.exists(os.path.join(old_user_dir, 'plugins')):
            shutil.move(os.path.join(old_user_dir, 'plugins'),
                        os.path.join(cf.USER_DIR, 'plugins'))
        shutil.rmtree(old_user_dir)

    def _datasources_db2url(self, dir_version, release):
        """Move data source config from userdb to datasources.cfg."""
        # Upgrade to 0.4.0: Data source are no longer stored in userdb.
        # TODO: Remove this hook in some upcoming major version.
        import cPickle
        from cf.db import Datasource
        from cf.db.url import URL
        from cf.ui import dialogs
        manager = DatasourceManager(self)
        x = self.userdb.get_table_version('datasource')
        if x is None:  # already dropped
            return
        sql = ('select name, description, backend, options, password '
               'from datasource')
        attribs = ['database', 'host', 'port', 'user']
        try:
            self.userdb.cursor.execute(sql)
            attribs.append('password')
        except sqlite3.OperationalError:  # password column is already gone
            sql = ('select name, description, backend, options '
                   'from datasource')
            self.userdb.cursor.execute(sql)
        ldap_found = False
        for item in self.userdb.cursor.fetchall():
            old_backend = item[2].split('.')[-1]
            opts = cPickle.loads(str(item[3]))
            if old_backend in ('mssql', 'oracle', 'mysql', 'postgres'):
                url = URL(old_backend)
                for name in attribs:
                    if name in opts:
                        setattr(url, name, opts[name])
                if len(item) == 5:
                    url.password = item[4]
                ds = Datasource(manager)
                ds.url = url
                ds.name = item[0]
                ds.decription = item[1]
                ds.ask_for_password = opts.get('ask_for_password', False)
                manager.save(ds)
            elif old_backend == 'sqlite':
                url = URL(old_backend)
                url.database = opts.get('filename', None)
                ds = Datasource(manager)
                ds.url = url
                ds.name = item[0]
                ds.description = item[1]
                ds.ask_for_password = opts.get('ask_for_password', False)
                manager.save(ds)
            elif old_backend == 'ldap':
                ldap_found = True
        if ldap_found:
            dialogs.warning('Warning',
                            'Sorry, LDAP server are no longer supported.')
        self.userdb.drop_table('datasource')

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
        create_editor = not args
        instance = MainWindow(self, create_editor=create_editor)
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
        gobject.idle_add(t.start)

    def show_help(self, topic='index'):
        """Opens a webbrowser with a help page.

        Arguments:
          topic: If given, the URL points to the selected topic.
        """
        url = os.path.join(MANUAL_URL, '%s.html' % topic)
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

    # ------------------
    # Resources helpers
    # ------------------

    def get_glade_file(self, filename):
        """Expands filename to full path pointing to Glade file."""
        return os.path.join(DATA_DIR, 'glade', filename)

    def load_icon(self, icon_name, size=None, lookup_method=None):
        """Wrapper for gtk.IconTheme.load_icon that catches GError."""
        if size is None:
            size = gtk.ICON_SIZE_MENU
        if lookup_method is None:
            lookup_method = (gtk.ICON_LOOKUP_FORCE_SVG |
                             gtk.ICON_LOOKUP_USE_BUILTIN |
                             gtk.ICON_LOOKUP_GENERIC_FALLBACK)
        if sys.platform.startswith('win'):
            lookup_method = (gtk.ICON_LOOKUP_NO_SVG |
                             gtk.ICON_LOOKUP_USE_BUILTIN |
                             gtk.ICON_LOOKUP_GENERIC_FALLBACK)
        try:
            return self.icon_theme.load_icon(icon_name, size, lookup_method)
        except gobject.GError, err:
            logging.warning(err)
            return self.icon_theme.load_icon('gtk-missing-image',
                                             size, lookup_method)

    def set_status_message(self, msg, context=1):
        for window in self.get_instances():
            window.statusbar.set_message(msg, context)

    def pop_status_message(self, context=1):
        for window in self.get_instances():
            window.statusbar.pop(context)

    def set_status_message(self, msg, context=1):
        for window in self.get_instances():
            window.statusbar.set_message(msg, context)

    def pop_status_message(self, context=1):
        for window in self.get_instances():
            window.statusbar.pop(context)


class CFAppCallbacks(gobject.GObject):
    """Container for application specific signals.

    :Signals:

    instance-created
      ``def callback(application, instance, user_data1, ...)``

      Called when a new instance was created
    """

    __gsignals__ = {
        "instance-created" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT,)),
    }
