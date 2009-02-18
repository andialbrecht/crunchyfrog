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

"""Python shell plugin"""

import logging

import gtk
import gobject

from cf.backends.schema import Table
from cf.plugins.core import BottomPanePlugin
from cf.plugins.mixins import InstanceMixin
from cf.ui.pane import PaneItem

try:
    from ipython_view import *
    HAVE_IPYTHON = True
except ImportError, err:
    logging.error(err)
    HAVE_IPYTHON = False


class CFShell(BottomPanePlugin, InstanceMixin):

    id = "crunchyfrog.plugin.cfshell"
    name = _(u"Shell")
    description = _(u"Interactive shell (mainly for debugging)")
    icon = "gnome-terminal"
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://cf.andialbrecht.de"
    version = "0.1"

    def __init__(self, app):
        BottomPanePlugin.__init__(self, app)
        self._instances = dict()

    def init_instance(self, instance):
        if instance in self._instances:
            return
        view = CFShellView(self.app, instance)
        instance.bottom_pane.add_item(CFShellView(self.app, instance))
        self._instances[instance] = view

    def shutdown(self):
        while self._instances:
            instance, view = self._instances.popitem()
            view.destroy()

if not HAVE_IPYTHON:
    CFShell.INIT_ERROR = _(u'Python module ipython is required.')


class CFShellView(gtk.ScrolledWindow, PaneItem):

    name = _(u'Shell')
    icon = 'gnome-terminal'
    detachable = True

    def __init__(self, app, instance):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.app = app
        self.instance = instance
        self.iview = IPythonView()
        self.iview.updateNamespace({"app": self.app,
                                    "window": self.instance})
        self.add(self.iview)
        self.set_size_request(-1, 100)
        self.show_all()
