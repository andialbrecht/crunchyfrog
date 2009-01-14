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

"""Builtin plugins"""

import logging

from cf.filter.exportfilter import CSVExportFilter
from cf.filter.exportfilter import OOCalcExportFilter

try: from cf.backends.ldapbe import LDAPBackend
except ImportError, err:
    logging.warning('Could not import LDAPBackend: %s', err)
try: from cf.backends.mysql import MySQLBackend
except ImportError, err:
    logging.warning('Could not import MySQLBackend: %s', err)
try: from cf.backends.postgres import PostgresBackend
except ImportError, err:
    logging.warning('Could not import PostgresBackend: %s', err)
try: from cf.backends.sqlite import SQLiteBackend
except ImportError, err:
    logging.warning('Could not import SQLiteBackend: %s', err)
try: from cf.backends.mssql import MsSQLBackend
except ImportError, err:
    logging.warning('Could not import MsSQLBackend: %s', err)

from cf.shell import CFShell
from cf.library import SQLLibraryPlugin
from cf.ui.refviewer import ReferenceViewer
