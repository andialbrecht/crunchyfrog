.. index::
   single: Data Sources; Native Command Line Clients

Native Database Shells
======================

For some databases you can access your database using the native command
line client, e.g. :command:`psql` for PostgreSQL or :command:`sqlplus` for
Oracle.

To open a native shell right click a data source in the navigator and
select :menuselection:`Open Native Shell`. A new tab containing a terminal
emulation is added to the main notebook.
If there's no such menu item, make sure that the native shell plugin is
activated and that the Python bindings for the VTE library (python-vte)
are installed on your system.

.. note::
   The command line arguments to connect to a data source are automatically
   set. Usually that means, that a password may be visible to other user
   when viewing the process list on the same computer.
