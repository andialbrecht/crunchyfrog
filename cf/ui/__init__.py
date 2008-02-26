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

import gobject
import gtk

from os.path import abspath, join, dirname

import cf

class GladeWidget(gobject.GObject):
    
    def __init__(self, app, xml, widget_name,
                 signal_autoconnect=True,
                 cb_provider=None):
        self.__gobject_init__()
        self.app = app
        if isinstance(xml, basestring):
            if not xml.endswith(".glade"):
                xml += ".glade"
            self.xml = gtk.glade.XML(join(cf.DATA_DIR, xml), widget_name)
        else:
            self.xml = xml
        if signal_autoconnect:
            if not cb_provider:
                cb_provider = self
            self.xml.signal_autoconnect(cb_provider)
        self.widget = self.xml.get_widget(widget_name)
        for item in dir(self.widget):
            if item.startswith("_") \
            or hasattr(self, item): continue
            setattr(self, item, getattr(self.widget, item))
        self.widget.set_data("glade-widget", self)
        self._setup_widget()
        self._setup_connections()
        
    def _setup_widget(self):
        """Called when the object is created."""
        
    def _setup_connections(self):
        """Called when the object is created."""
        