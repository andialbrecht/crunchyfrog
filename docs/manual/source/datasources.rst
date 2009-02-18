.. _datasources:

Managing Datasources and Connections
====================================

A data source tells :program:`CrunchyFrog` how to connect to a database.
Depending on the database a data source needs provider specific information.


.. _datasources_defining:

Configure Data Sources
----------------------

Data sources can be created, edited and deleted using the data source manager.
To open the data source manager choose:
:menuselection:`Edit --> Data Sources`.

A dialog with a notebook pops up. The notebook has two pages:

:guilabel:`Data Sources`
   Data Source configuration

:guilabel:`Connections`
   Database connection management (see :ref:`datasources_connections`)

To configure datasource select the :guilabel:`Data Sources` page.


.. _datasources-new:

Create a New Data Source
^^^^^^^^^^^^^^^^^^^^^^^^

To create a new data source, click on the :guilabel:`New` button.
A new data source requires a name, the description is optional. Choose
a database system from the drop down list. After choosing
a database system additional database specific fields are displayed.

To test if all values are correct, click on the :guilabel:`Test connection`
button.
:program:`CrunchyFrog` tries to open a connection to the database with
the given values. If an error occurs it will be displayed in a popup window.

If everything is ok, save the new datasource using the :guilabel:`Save`
button. The new data source will be listed in the list on the left.


.. _datasources-edit:

Edit a Data Source
^^^^^^^^^^^^^^^^^^

To edit an existing data source select the data source from the
list on the left. The values are displayed in the form and can
be edited. Click :guilabel:`Save` to save your changes.


.. _datasources-delete:

Delete a Data Source
^^^^^^^^^^^^^^^^^^^^

To delete a data source select the data source in the list on the left and
click :guilabel:`Delete`.


.. _datasources_connecting:

Connecting to a Database
^^^^^^^^^^^^^^^^^^^^^^^^

To connect to a database use one of the following methods:

Datasource Manager
   Open the datasource manager (:menuselection:`Edit --> Data Sources`),
   choose the :guilabel:`Connections` page,
   select the datasource you want to connect to and click
   on the :guilabel:`Connect` button.

Navigator
   If you double-click a datasource in the navigator a
   connection to the database will be established and
   a new SQL editor opens with this connection assigned.
   If there's already an active connection to this datasource
   the existing connection will be reused for the new
   SQL editor.

Menubar
   Select :menuselection:`Query --> Connection` to select an already
   opened connection or to open a new connection that should be assigned
   to the foreground editor.

Toolbar
   For an already opened SQL editor you can use the
   connection chooser widget in the toolbar to quickly
   select a connection. The connection chooser is bound
   to the currently active SQL editor.


Default Connection for New Editors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Except when a editor is created by double clicking a datasource entry in the
navigator, editors have no connection assigned by default.
You can change this behavior by enabling the
:guilabel:`Use active connection as default` in the preferences dialog.
If this option is active, new editors use the same connection as the current
foreground editor.


.. _datasources_connections:

About Database Connections
--------------------------

A data source can have multiple database connections opened at once.
But the navigator is always using the first opened connection. SQL editors
can use any database connection.

To keep track of the connections you have opened select
:guilabel:`Show connection` from the connection
chooser widget located at the toolbar. A handy dialog pops up where
you can close and create connections. It has the same functionality
as the :guilabel:`Connections` page on the data source manager.

.. note::

   Database connections are shared between all main windows.
