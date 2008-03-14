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

"""Release information"""

name = "CrunchyFrog"
appname = name.lower()
version = "0.2.0"
copyright = "Copyright (C) 2008 Andi Albrecht <albrecht.andi@gmail.com>"
description = "Database navigator and query tool for GNOME"
author = "Andi Albrecht"
author_email = "albrecht.andi@gmail.com"
url = "http://cf.andialbrecht.de"
long_description = """CrunchyFrog is a SQL editor and database schema browser for the GNOME desktop.

Supported databases
===================

 * PostgreSQL (requires psycopg2)
 * MySQL (requires MySQLdb)
 * SQLite3 (requires python-sqlite3)
 * Oracle (requires cx_Oracle)
 * LDAP (requires python-ldap)

It is written in Python (PyGTK) and provides a setuptools based plugin system, which is completely undocumented for now (read the source ;-)

Check out the Google pages for the most recent version."""
license = """This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""