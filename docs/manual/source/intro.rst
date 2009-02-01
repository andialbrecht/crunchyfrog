.. _intro:

Introduction
============

CrunchyFrog is a database front-end for Gnome.


.. _download:

Download and Installation
-------------------------


.. _requirements:

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


.. _getting-started:

Getting Started
---------------

This section explains how :ref:`start <crunchyfrog-start>` and how the
:ref:`main window <crunchyfrog-mainwindow>` looks like.

.. note::

   If you have any troubles running CrunchyFrog, make sure that all
   :ref:`requirements <requirements>` are met.


.. _crunchyfrog-start:

To Start CrunchyFrog
^^^^^^^^^^^^^^^^^^^^

You can start CrunchyFrog in the following ways:

:guilabel:`Applications` menu
   Choose :menuselection:`Development --> CrunchyFrog`.

Command line
   To start CrunchyFrog	from a command line, type the following command,
   then press :kbd:`Return`: :command:`crunchyfrog [FILE1, FILE2, ...]`
   where `FILE1` and `FILE2` are optional filenames of files you want to open.

   CrunchyFrog opens each file that you specify in the same window.
   If another instance of CrunchyFrog is running, CrunchyFrog opens
   a dialog where you can choose, if you want to open the
   specified files in an existing or a new instance of CrunchyFrog.


.. _crunchyfrog-mainwindow:

Main Window
^^^^^^^^^^^

When you start CrunchyFrog, the following window is displayed.

.. image:: figures/cf-main.png

The CrunchyFrog window has the following elements:

Menubar
   The menus on the menubar contain all of the commands
   you need to work with files in CrunchyFrog.
   Plugins can add additionally menus to the menubar.

Toolbar
   The toolbar contains a subset of the commands that you
   can access from the menubar.

Display area
   The display area has different elements, depending
   on the activated plugins. By default, the display
   area contains the database navigator on the left
   and a placeholder for SQL editors on the right.

Statusbar
   The statusbar displays information about current
   CrunchyFrog activity and contextual information about selected elements.

