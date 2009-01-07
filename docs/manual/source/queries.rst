.. _crunchyfrog-queries:

Database Queries
================

.. _sqleditor:

SQL Editor
----------

A SQL editor can be opened in the following ways:

Menubar
   Choose :menuselection:`File --> New --> Query`

Toolbar
   Click on the first button

Shortcut Key
   Press :kbd:`Ctrl+N`

Navigator
   Double click on any datasource

.. tip::
   Except when opening an editor by double-clicking on a datasource
   in the navigator, a new SQL editor is not bound to a connection.


A SQL editor has two parts:

Query
   Textarea to enter queries

Results Panel
   The results panel below the textarea has the three
   tabs :guilabel:`Results`, :guilabel:`Explain` and :guilabel:`Messages`.


.. _queries_execute:

Executing Queries
-----------------

To execute a query press :kbd:`F5` or
click on the execute button in the toolbar. The result of
a query will be displayed in the results panel, when the
query has finished.

.. caution::
   Unfortunately the SQL editor has no integrated SQL parser
   for now. If the SQL editor or the selected text has more
   then one statement, all statements are executed by the
   current connection at once.
   But only the return value or the result of the last query
   will be displayed in the results pane.


.. tip::
   Statements can contain placholders. Placeholders begin with
   a dollar sign followed by one or more letters and numbers.
   If you user placeholders a dialog pops up before the query is
   executed where you can replace the placeholders with concrete
   values.
   To disable this function open the preferences dialog:
   :menuselection:`Editor --> General --> Replace variables`



.. _queries_results:

Query Results
-------------

If a query returns data from your database, they are displayed
in the results panel within the :guilabel:`Results` tab.

.. caution::
   :program:`CrunchyFrog` displays alwas **all** returned rows.
   This can result in perfomance issues under some circumstances.

   If displaying a huge dataset results in performance issues
   depends on both the number of rows and the number of
   columns that are displayed in the data grid.
   A query that returns 350.000 rows with 12 columns could
   result in better performance of the result grid than a
   query that returns only 10.000 rows with a lot of columns.

You can select parts of the data displayed in the data grid in the
following ways:

Rows
   Click on the row number in the first column to select a whole row.

Columns
   Click on the column header to select a whole column.

Cells
   Click on a cell to select individual cells.

Select/Unselect All
   To select or unselect all cells click on the first (top left) cell.

Click on the :guilabel:`Copy` button in the toolbar
in an editor to copy selected cells, columns or rows to the clipboard.

To export the dataset click on the :guilabel:`Export`
button in the toolbar. If you have made a selection before,
the export dialog gives you an option to export only the selected data.


.. _queries_transactions:

Transactions
------------

If it's supported by the database backend, transactions can be
used using the buttons in the toolbar. The transaction state
can be changed by statements executed in the editor, too.
