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

import bonobo
import gobject

import sys

from cf import release
from config import Config # IGNORE:E0611
from datasources import DatasourceManager
from plugins.core import PluginManager
from ui.prefs import PreferencesDialog
from userdb import UserDB

import logging
log = logging.getLogger("APP")

class CFApplication(bonobo.Application):
    """Main application object
    
    :Attributes:
        config: preferences
        userdb: uer database
        plugins: pugin manager
        datasources: datasource manager
    
    """
    
    def __init__(self, options):
        bonobo.Application.__init__(self, release.name)
        self.options = options
        self.cb = CFAppCallbacks()
        self.__shutdown_tasks = []
        self.config = Config(self, options.config)
        self.userdb = UserDB(self)
        self.plugins = PluginManager(self)
        self.datasources = DatasourceManager(self)
        
    def get_instances(self):
        ret = self.get_data("instances")
        if not ret:
            ret = []
        return ret
        
    def preferences_show(self):
        """Displays the preferences dialog"""
        dlg = PreferencesDialog(self)
        dlg.run() # IGNORE:E1101 - Generic method
        dlg.destroy() # IGNORE:E1101 - Generic method
        
    def register_shutdown_task(self, func, msg, *args, **kwargs):
        """Registers a new shutdown task.
        
        :param func: a callable
        :param msg: a human-readable message explaining what this task does
        :param args, kwargs: arguments and kw arguments for this task
        """
        self.__shutdown_tasks.append((func, msg, args, kwargs))
        
    def shutdown(self):
        """Execute all shutdown tasks and quit application"""
        while self.__shutdown_tasks:
            func, msg, args, kwargs = self.__shutdown_tasks.pop()
            log.info(msg)
            try:
                func(*args, **kwargs)
            except:
                log.error("Task failed: %s" % str(sys.exc_info()[1])) 
        
class CFAppCallbacks(gobject.GObject):
    
    __gsignals__ = {
        "instance-created" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT,)),
    }