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

"""User interface"""

import logging

import gobject
import gtk

from os.path import abspath, join, dirname

import cf

class GladeWidget(gobject.GObject):
    """Helper for Glade widgets

    This class is a helper for widgets defined in Glade files. It
    shouldn't be used directly.

    Upon intialization the two methods ``_setup_widget()`` and
    ``_setup_connections()`` are called.

    Read the source of one of the subclasses to get an idea how
    this class works.

    :Instance attributes:

        :app: `CFApplication`_ instance
        :xml: `gtk.glade.XML`_ instance
        :widget: The *real* GTK widget

    .. _CFApplication: cf.app.CFApplication.html
    .. _gtk.glade.XML: http://pygtk.org/docs/pygtk/class-gladexml.html
    """

    def __init__(self, win, xml, widget_name,
                 signal_autoconnect=True,
                 cb_provider=None):
        """
        This constructor takes up to five arguments:

        :Parameter:
            app
                `CFApplication`_ instance
            xml
                Glade source
            widget_name
                Name of the widget to fetch
            signal_autoconnect
                Auto-connect signals (optional, default ``True``)
            cb_provider
                Argument for ``signal_autoconnect`` (optional)

        If ``xml`` is a string it is assumed that it is the name of
        a Glade file located in the data directory. If it's a `gtk.glade.XML`_
        instance, this instance is taken as the widget source.

        If ``signal_autoconnect`` is ``True`` the ``signal_autoconnect()`` method
        of the `gtk.glade.XML`_ instance is called upon initialization.
        If the optional ``cb_provider`` argument is given, it will be used as
        the parameter for ``signal_autoconnect()``. Otherwise
        ``signal_autoconnect(self)`` is called.

        .. _CFApplication: cf.app.CFApplication.html
        .. _gtk.glade.XML: http://pygtk.org/docs/pygtk/class-gladexml.html
        """
        self.__gobject_init__()
        self.win = win
        if self.win and hasattr(win, 'app'):
            self.app = win.app
        else:
            self.app = None
        if isinstance(xml, basestring):
            if not xml.endswith(".glade"):
                xml += ".glade"
            glade_file = join(cf.DATA_DIR, 'glade/', xml)
            logging.info('Loading Glade file %r' % glade_file)
            self.xml = gtk.glade.XML(glade_file, widget_name)
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
