#### To run CrunchyFrog on your system: ####

  * Python (>=2.5, <3.0)
  * PyGObject (>=2.14)
  * PyGTK (>= 2.12, incl. Glade bindings)
  * ConfigObj (>= 4.4.0)
  * pygtksourceview2 (>= 2.4.0)
  * python-cairo (>= 1.4.0)
  * python-xdg (>= 0.15)
  * python-sqlparse (>= 0.1.1)

<a href='Hidden comment: 
For the development version (trunk, unstable) you"ll need in addition:
'></a>


#### Optional Requirements ####

Depending on which databases you want to access with CrunchyFrog
you'll need additional Python modules installed:

  * for PostgreSQL: `psycopg2`
  * for MySQL: `MySQLdb`
  * for SQLite3 no additional modules are required
  * for Oracle: `cx_Oracle`
  * for MSSQL: `pymssql`
  * for Firebid: `kinterbasdb`
  * for Informix: `informixdb`
  * for MaxDB: `sapdb`

Installing Oracle drivers:

> Installing the Python drivers for Oracle isn't as easy as `pip install thedriver`. Here are some blog posts that may help:

> http://catherinedevlin.blogspot.it/2008/06/cxoracle-and-oracle-xe-on-ubuntu.html

> http://ubuntuxtutti.blogspot.de/2012/09/installiamo-oracle-booom.html (italian)

When running in GNOME desktop environment it's recommended to have the
following modules installed to benefit from a tighter integration with
the desktop environment:

  * python-gnome2
  * python-gconf

To use the builtin Python shell `ipython` needs to be installed.

To export results in Excel format `python-xlwt` needs to be installed.

To export results in OpenOffice format `python-ooolib` needs to be
installed.

#### To install CrunchyFrog on your system you'll need in addition: ####

  * python-sphinx