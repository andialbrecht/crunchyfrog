.. _datasources:

Datasources and Connections
===========================

A datasource tells :program:`CrunchyFrog` how to connect to a database.
Depending on the database a datasource needs provider specific information.


.. _datasources_defining:

Datasource Configuration
------------------------

Datasource can be created, edited and deleted using the datasource manager.
To open the datasource manager choose:
:menuselection:`Edit --> Datasource Manager`.

A dialog with a notebook pops up. The notebook has two pages:

:guilabel:`Datasources`
   Datasource configuration

:guilabel:`Connections`
   Database connection management (see :ref:`datasources_connections`)

To configure datasource select the :guilabel:`Datasources` page.


.. _datasources-new:

Create a New Datasource
^^^^^^^^^^^^^^^^^^^^^^^

To create a new datasource, click on the :guilabel:`New` button.
A new datasources requires a name, the description is optional. Choose
a database system from the drop down list. After choosing
a database system additional database specific fields are displayed.

To test if all values are correct, click on the :guilabel:`Test connection`
button.
:program:`CrunchyFrog` tries to open a connection to the database with
the given values. If an error occurs it will be displayed in a popup window.

If everything is ok, save the new datasource using the :guilabel:`Save`
button. The new datasource will be listed in the list on the left.


.. _datasources-edit:

Edit a Datasource
^^^^^^^^^^^^^^^^^

To edit an existing datasource select the datasource in the
list on the left. The values are displayed in the form and can
be edited. Click :guilabel:`Save` to save your changes.


.. _datasources-delete:

Delete a Datasource
^^^^^^^^^^^^^^^^^^^

To delete a datasource select the datasource in the list on the left and
click :guilabel:`Delete`.


.. _datasources_connecting:

Connect to a Database
^^^^^^^^^^^^^^^^^^^^^

To connect to a database use one of the following methods:

Datasource Manager
   Open the datasource manager (:menuselection:`Edit --> Datasource Manager`),
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

Toolbar
   For an already opened SQL editor you can use the
   connection chooser widget in the toolbar to quickly
   select a connection. The connection chooser is bound
   to the currently active SQL editor.


.. _datasources_connections:

About Database Connections
--------------------------

A datasource can have multiple open database connections. But the
navigator is always using the first opened connection. SQL editors
can use any database connection. You can choose a connection for
an SQL editor using the connection choooser widget in the toolbar.

To keep track of the connections you have opened select
:guilabel:`Show connection` from the connection
chooser widget located at the toolbar. A handy dialog pops up where
you can close and create connections. It has the same functionality
as the :guilabel:`Connections` page on the data source manager.

.. warning::

   Database connection are the same for all instances of
   :program:`CrunchyFrog`!
