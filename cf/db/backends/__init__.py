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

"""Database backends."""

from cf.db import DIALECTS
from cf.db import objects
from cf.db import TRANSACTION_IDLE
from cf.db import TRANSACTION_COMMIT_ENABLED
from cf.db import TRANSACTION_ROLLBACK_ENABLED
from cf.db.url import make_url, URL


class GUIOption(object):

    WIDGET_PASSWORD = 'password'
    WIDGET_PORT = 'port'
    WIDGET_CHECKBOX = 'checkbox'
    WIDGET_FILECHOOSER = 'filechooser'
    WIDGET_COMBO = 'combo'

    def __init__(self, key, label, widget=None, required=False,
                 choices=None, tooltip=None):
        self.key = key
        self.label = label
        self.widget = widget
        self.required = required
        self.choices = choices
        self.tooltip = tooltip


DEFAULT_OPTIONS = (
    GUIOption('host', _(u'Host')),
    GUIOption('port', _(u'Port'),
              widget=GUIOption.WIDGET_PORT),
    GUIOption('database', _(u'Database')),
    GUIOption('username', _(u'Username')),
    GUIOption('password', _(u'Password'),
              widget=GUIOption.WIDGET_PASSWORD),
    )


class Generic(object):

    drivername = None

    @classmethod
    def get_options(cls):
        """Return a list of :class:`GUIOption` instances.

        Backend implementations can overwrite this method to provide
        appropriate options. The default implementation returns a single
        option to give the URL directly.
        """
        return (GUIOption('url', _(u'URL'), required=True),)

    @classmethod
    def create_url(cls, options):
        """Create an URL from options.

        :param options: A dictionary mapping :class:`GUIOption` keys with
            values from UI.

        :returns: An :class:`URL` instance.
        """
        url = URL(cls.drivername)
        for key in ('username', 'password', 'host', 'port', 'database'):
            if key in options and options.get(key, None) is not None:
                setattr(url, key, options[key])
        return url

    @classmethod
    def get_native_shell_command(cls, url):
        """Return command and arguments to connect to native db shells.

        The default implementation returns ``None`` which disabled the
        native shell for this backend. If a native shell is available for
        this backend the method must return a 2-tuple (command, argv).
        """
        return None

    @classmethod
    def get_connect_params(cls, url):
        """Convert URL to connection arguments and keyword arguments."""
        return tuple(), url.get_dict()

    @classmethod
    def dbapi(cls):
        """Returns the DB-API2 module."""
        msg = 'Driver.dbapi() not implemented [%s]' % cls.drivername
        raise NotImplementedError(msg)

    def get_connection(self, url):
        """Returns a DB-API2 connection."""
        args, kwds = self.get_connect_params(url)
        conn = self.dbapi().connect(*args, **kwds)
        return conn

    def prepare_connection(self, dbapi_connection):
        """Prepares the DB-API2 connection.

        This method can be overwritten by backend implementations and is
        called after the DB-API2 connection is opened. The default
        implementation does nothing.
        """
        pass

    def get_server_info(self, connection):
        """Return human-readable server version info."""
        return DIALECTS[self.drivername]['name']

    def prepare_statement(self, sql):
        """Prepare statement before executing."""
        return sql

    def initialize(self, meta, connection):
        """Initialize basic meta data.

        Backend implentations should overwrite this method to provide
        initial meta information about database objects (e.g. table,
        view and column names). Additional information may be fetched during
        runtime using the :meth:`refresh` and :meth:`get_children` methods.
        The meta information initialized here is mainly used for
        auto-completion.

        The default implementation does nothing.
        """
        pass

    def refresh(self, parent, meta, connection):
        """Refresh child objects for parent."""
        pass

    def get_transaction_state(self, connection):
        """Determine transaction state for connection.

        This method can be overwritten by backend implementations to
        find a more precise answer.
        """
        return TRANSACTION_IDLE

    def begin(self, connection):
        """Begin transaction. Return True if handled."""
        connection.execute('BEGIN')
        return True

    def get_explain_statement(self, statement):
        """Return a SQL for executing EXPLAIN or None."""
        return "EXPLAIN %s" % statement
