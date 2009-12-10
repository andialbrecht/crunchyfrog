# -*- coding: utf-8 -*-

# crunchyfrog - a database schema browser and query tool
# Copyright (C) 2009 Andi Albrecht <albrecht.andi@gmail.com>
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

"""Database meta information."""

from gettext import gettext as _

import logging
import thread

import gobject
import gtk




class DatabaseMeta(object):

    def __init__(self, datasource):
        self.datasource = datasource
        self.app = datasource.manager.app
        self.conn = self.datasource.internal_connection
        self._items = set()
        if self.conn.threadsafety >= 2:
            thread.start_new_thread(self.initialize, (True,))
        else:
            self.initialize()

    @property
    def backend(self):
        return self.datasource.backend

    def get_server_info(self):
        return self.backend.get_server_info(self.conn)

    def initialize(self, threaded=False):
        """Called after instance creation to prepare intial data."""
        if threaded:
            gtk.gdk.threads_enter()
        self.app.set_status_message(_(u'Loading database structure...'), 100)
        if threaded:
            gtk.gdk.threads_leave()
        try:
            self.backend.initialize(self, self.conn)
        except:
            msg = 'DatabaseMeta.initialize failed (driver: %s):'
            msg = msg % self.backend.drivername
            logging.exception(msg)
        if threaded:
            gtk.gdk.threads_enter()
        self.app.pop_status_message(100)
        if threaded:
            gtk.gdk.threads_leave()

    def set_object(self, obj):
        """Adds or replaces an object."""
        if obj in self._items:
            self._items.remove(obj)
        self._items.add(obj)

    def get_children(self, parent=None):
        """Get child objects for parent."""
        if parent is not None and parent.props.refresh_required:
            self.backend.refresh(parent, self, self.conn)
            parent.props.refresh_required = False
        return self.find(parent=parent)

    def find(self, **kwds):
        """Find an object using searchterm."""
        res = list(self._items)
        if 'cls' in kwds:
            objcls = kwds.pop('cls')
            res = filter(lambda x: isinstance(x, objcls), res)
        for key, value in kwds.iteritems():
            res = filter(lambda x: x.property_matches(key, value), res)
        return res

    def find_exact(self, **kwds):
        """Like :meth:`find`, but returns exactly one match or ``None``."""
        res = self.find(**kwds)
        if len(res) > 1:
            raise RuntimeError('More than one match found (%d)' % len(res))
        elif len(res) == 1:
            return res[0]
        return None
