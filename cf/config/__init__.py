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

# $Id: __init__.py 127 2008-02-25 10:50:10Z freshi $

"""Configuration"""

import gobject

from os.path import abspath, dirname, join
from configobj import ConfigObj

from gettext import gettext as _

from cf import USER_CONF

class Config(gobject.GObject):
    """Configuration object"""
    
    __gsignals__ = {
        "changed" : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (str, gobject.TYPE_PYOBJECT)),
    }
    
    def __init__(self, app):
        self.app = app
        self.__gobject_init__() # IGNORE:E1101
        self.__conf = None
        self.__init_conf()
        self.app.register_shutdown_task(self.on_app_shutdown, 
                                        _(u"Writing configuration"))
        
    def on_app_shutdown(self, *args): # IGNORE:W0613
        """Callback: write configuration file to disk"""
        self.write()
        
    def __init_conf(self):
        """Intialize the configuration system"""
        self.__conf = ConfigObj(abspath(join(dirname(__file__), "default.cfg")),
                                unrepr=True)
        self.__conf.update(ConfigObj(USER_CONF, unrepr=True))
        
    def init(self):
        """Loads configuration"""
        pass
        
    def get(self, key, default=None):
        """Returns value or default for key"""
        return self.__conf.get(key, default)
    
    def set(self, key, value):
        """Sets key to value"""
        self.__conf[key] = value
        self.emit("changed", key, value) # IGNORE:E1101
        
    def write(self, fname=None):
        """Writes configuration file"""
        if not fname:
            fname = USER_CONF
        fp = open(USER_CONF, "w")
        self.__conf.write(fp)
        fp.close()