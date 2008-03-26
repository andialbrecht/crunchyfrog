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

"""DBus service and client"""

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

main_loop = DBusGMainLoop()
bus = dbus.SessionBus(mainloop=main_loop)

DBUS_NAME = "org.gnome.crunchyfrog"
DBUS_PATH = "/org/gnome/crunchyfrog"

class CFService(dbus.service.Object):
    """DBus service"""
    
    def __init__(self, app):
        global bus
        bus_name = dbus.service.BusName(DBUS_NAME, bus=bus)
        dbus.service.Object.__init__(self, bus_name, DBUS_PATH)
        self.app = app
        
    @dbus.service.method(DBUS_NAME)
    def new_instance(self):
        """Creates a new instance.
        
        :Returns: Instance ID
        """
        instance = self.app.new_instance()
        return instance.get_data("instance-id")
    
    @dbus.service.method(DBUS_NAME)
    def open_uri(self, instance_id, uri):
        """Opens an URI 
        
        :Parameter:
            instance_id
                An instance ID
            uri
                An URI
        """
        instance = self.app.get_instance(instance_id)
        editor = instance.new_editor(uri)
        
    @dbus.service.method(DBUS_NAME)
    def get_instances(self):
        """Returns running instances.
        
        The return value is a list of 2-tuples instance_id, window title.
        """
        ret = []
        for key, value in self.app.get_data("instances").items():
            ret.append((key, value.widget.get_title()))
        return ret
        

def get_client():
    """Returns a DBus client"""
    global bus
    return bus.get_object(DBUS_NAME, DBUS_PATH)