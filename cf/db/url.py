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

"""Data source URL"""

import logging
import urlparse
try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

import cf.db

def _initialize():
    # Customize urlparse
    global _intialized
    if _initialized:
        return
    [urlparse.uses_netloc.append(drivername)
     for drivername in cf.db.DIALECTS
     if drivername not in urlparse.uses_netloc]

    [urlparse.uses_query.append(drivername)
     for drivername in cf.db.DIALECTS
     if drivername not in urlparse.uses_query]

    _intialized = True

_initialized = False


class URL(object):

    def __init__(self, drivername, user=None, password=None,
                 host=None, port=None, database=None, **kwds):
        self.drivername = drivername
        self.user = user
        self.password = password
        self.host = host
        self.port = self._clean_port(port)
        self.database = database
        self.query = kwds
        _initialize()

    def _get_username(self):
        return self.user

    def _set_username(self, username):
        self.user = username

    username = property(fget=_get_username, fset=_set_username)

    def __str__(self):
        netloc = ''
        if self.user:
            netloc += self.user
        if self.password:
            netloc += ':%s' % self.password
        if self.user:
            netloc += '@'
        if self.host:
            netloc += self.host
        if self.port:
            netloc += ':%s' % self.port
        if self.database and self.database.startswith('/'):
            netloc += '/'
        if self.query:
            query = '%s' % '&'.join(['%s=%s' % (k, v)
                                     for k, v in self.query.iteritems()])
        else:
            query = None
        return urlparse.urlunsplit((self.drivername, netloc,
                                    self.database or '', query, None))

    @classmethod
    def _clean_port(cls, port):
        """Return port as integer or None."""
        if port is None:
            return port
        if not isinstance(port, int):
            try:
                port = int(port)
            except (TypeError, ValueError), err:
                port = None
                logging.exception('Failed to convert port to int %r: %s',
                                  port, err)
        return port

    def get_dict(self):
        """Return instance values as dictionary."""
        data = {}
        if self.user:
            data['username'] = self.user
        if self.password:
            data['password'] = self.password
        if self.host:
            data['host'] = self.host
        if self.port:
            data['port'] = self.port
        if self.database:
            data['database'] = self.database
        data.update(self.query)
        return data


def make_url(raw):
    """Create URL from string."""
    _initialize()
    parsed = urlparse.urlsplit(raw)
    if (parsed.path and parsed.path.startswith('/')
        and not parsed.path.startswith('//')):
        database = parsed.path[1:]
    else:
        database = parsed.path or None
    if database and database.startswith('//'):
        database = database[1:]
    if parsed.query:
        kwds = dict(parse_qsl(parsed.query))
    else:
        kwds = {}
    return URL(parsed.scheme,
               parsed.username or None, parsed.password or None,
               parsed.hostname or None, parsed.port or None,
               database, **kwds)
