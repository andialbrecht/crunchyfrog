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

"""Oracle backend"""

from cf.db.backends import Generic, GUIOption


class Oracle(Generic):

    drivername = 'oracle'

    @classmethod
    def dbapi(cls):
        import cx_Oracle
        return cx_Oracle

    @classmethod
    def get_native_shell_command(cls, url):
        args = []
        logon = ''
        if url.user:
            logon += url.user
        if url.password:
            logon += '/%s' % url.password
        if url.host:
            logon += '@%s' % url.host
        if 'mode' in url.query and url.query['mode']:
            logon += ' AS %s' % url.query['mode']
        args.extend([logon])
        return 'sqlplus', args

    @classmethod
    def get_connect_params(cls, url):
        # derived from sqlalchemy.databases.oracle
        if url.database:
            # if we have a database, then we have a remote host
            port = url.port
            if port:
                port = int(port)
            else:
                port = 1521
            dsn = self.dbapi().makedsn(url.host, port, url.database)
        else:
            # we have a local tnsname
            dsn = url.host

        opts = dict(user=url.username, password=url.password, dsn=dsn)
        if 'mode' in url.query:
            opts['mode'] = url.query['mode']
            if isinstance(opts['mode'], basestring):
                mode = opts['mode'].upper()
                if mode == 'SYSDBA':
                    opts['mode'] = self.dbapi().SYSDBA
                elif mode == 'SYSOPER':
                    opts['mode'] = self.dbapi().SYSOPER
                else:
                    opts['mode'] = int(opt['mode'])
        return tuple(), opts

    @classmethod
    def get_options(cls):
        return (
            GUIOption('host', _(u'TNS Name')),
            GUIOption('username', _(u'Username')),
            GUIOption('password', _(u'Password'),
                      widget=GUIOption.WIDGET_PASSWORD),
            GUIOption('mode', _(u'Mode'),
                      widget=GUIOption.WIDGET_COMBO,
                      choices=(
                          (None, None),
                          ('SYSDBA', 'SYSDBA'),
                          ('SYSOPER', 'SYSOPER'),
                      )),
            )

    def get_server_info(self, connection):
        return 'Oracle %s' % connection.connection.version

    def prepare_statement(self, sql):
        # See issue50: cx_Oracle requires str or None for cursor.execute().
        sql = str(sql)
        # Another issue: Somehow Oracle dislikes trailing semicolons.
        # Maybe this approach is a little bit crude, but just remove it...
        # See this thread for example:
        # http://www.mail-archive.com/django-users@googlegroups.com/msg11479.html
        sql = sql.strip()
        if sql.endswith(';'):
            sql = sql[:-1]
        return str(sql)

DRIVER = Oracle
