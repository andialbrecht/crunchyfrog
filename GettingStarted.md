## Running CrunchyFrog ##

To download and run CrunchyFrog from a released version execute
the following command in a terminal:

```
  $ wget http://crunchyfrog.googlecode.com/files/crunchyfrog-0.4.1.tar.gz
  $ tar xvfz crunchyfrog-0.4.1.tar.gz
  $ cd crunchyfrog-0.4.1/
  $ ./crunchyfrog
```

Make sure that all [required](Requirements.md) Python modules are installed.


For a localized version first run

```
  python setup.py compile_mo
```

to generate the compiled message catalogs.


To open the manual using the "Help" menu item run

```
  python setup.py build_manual
```

to generate the HTML version of the manual.


## Installing CrunchyFrog on Your System ##

For a system-wide installation run:

```
  sudo python setup.py install
```

Alternatively you can look for [pre-built binaries](PreBuiltBinaries.md)
for your distribution.


## First Steps: Create a Database Connection ##

**Note:** Not all plugins are activated by default. So it's an good idea to
have a look at the plugins configuration (Edit > Plugins) and the preferences
(Edit > Preferences) first.
You will need at least one active database backend.

The next thing is to define some datasources by opening the datasource
manager (Edit > Data Source Manager).
When you have defined your data source and closed the dialog,
double-click the new entry in CrunchyFrog's sidebar to connect to
your database and to open a SQL editor with that connection assigned.

Refer to the
[manual](http://packages.python.org/crunchyfrog/)
for additional information on how to use this application.