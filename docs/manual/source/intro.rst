Introduction
============

CrunchyFrog is a database front-end for Gnome.


Download and Installation
-------------------------


Requirements
------------

 * Python >= 2.5
 * PyGTK >= 2.12
 * python-setuptools
 * GNOME bindings, including extras (gtksourceview2, gnomekeyring)
 * GConf bindings
 * python-pysqlite2 >= 2.0.5
 * python-configobj >= 4.4.0
 * python-lxml >= 0.9
 * gnome-extra-icons
 * python-sexy

The following modules are required for specific database backends:

 * psycopg2 (optional, required to connect to PostgreSQL databases)
 * MySQLdb (optional, required to connect to MySQL databases)
 * sqlite3 bindings (optional, required to connect to SQLite3 databases)
 * cx_Oracle (optional, required to connect to Oracle databases)
 * ldap bindings (optional, required to browse LDAP servers)
 * pymssql bindings (optional, required to connect to SQL Server)
