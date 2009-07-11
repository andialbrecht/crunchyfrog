.. _crunchyfrog-queries:

Database Queries
================

.. index::
   single: Editor
   single: User Interface; Editor

.. _sqleditor:

SQL Editor
----------

A SQL editor can be opened in the following ways:

Menubar
   Choose :menuselection:`File --> New --> Query`

Toolbar
   Click on the button labeled :guilabel:`Query`

Shortcut Key
   Press :kbd:`Ctrl+N`

Navigator
   Double click on any datasource


A SQL editor has two parts:

Query
   Textarea to enter queries

Results Panel
   The results panel below the textarea has the three
   tabs :guilabel:`Results`, :guilabel:`Explain` and :guilabel:`Messages`.


.. index::
   single: Query; Execute

.. _queries_execute:

Executing Queries
-----------------

To execute a query press :kbd:`F5` or
click on the execute button in the toolbar. The result of
a query will be displayed in the results panel, when the
query has finished.

If no text is selected, all statements in the editor are executed.

Select one or more statements to execute the selected statements only.

Press :kbd:`Ctrl+F5` to execute the statement at the current cursor
location.

.. tip::
   Statements can contain placholders. Placeholders begin with
   a dollar sign followed by one or more letters and numbers.
   If you user placeholders a dialog pops up before the query is
   executed where you can replace the placeholders with concrete
   values.
   To disable this function open the preferences dialog:
   :menuselection:`Editor --> General --> Replace variables`



.. index::
   single: Results
   single: User Interface; Query Results

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

Click on the :guilabel:`Copy` button in the toolbar or hit
:kbd:`Ctrl+C` to copy selected cells, columns or rows to the clipboard.

To export the dataset click on the :guilabel:`Export`
button in the toolbar. If you have made a selection before,
the export dialog gives you an option to export only the selected data.


.. index::
   pair: Query; Transactions
   pair: Connection; Transactions

.. _queries_transactions:

Transactions
------------

If it's supported by the database backend, transactions can be
used using the buttons in the toolbar. The transaction state
can be changed by statements executed in the editor, too.


Editing SQL Statements
----------------------

The editor provides features for editing SQL statements.


.. index::
   pair: Editor; Navigation

Navigating Between Statements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To navigate between statements in the SQL editor use :kbd:`Ctrl+Alt+J`
to jump to the next statement and :kbd:`Ctrl+Alt+K` to jump to the
previous statement.


.. index::
   pair: Editor; Autocompletion

Autocompletion
^^^^^^^^^^^^^^

The editor supports autocompletion for tables, columns and SQL syntax.
To activate autocompletion press :kbd:`Ctrl+Space` while typing
a SQL statement. If there's more than one possible completion you can
select the desired completion from a popup list.
Use the arrow keys to navigate through this list, :kbd:`Enter` to write the
selected item in the editor window or :kbd:`Escape` to cancel this operation.
Any other key will narrow down the list of possible completions.

A more advanced approach is to activate :guilabel:`Tab Starts Autocompletion`
in the preferences dialog. If this option is activated, :kbd:`Tab` omits the
popup if there's exactly one completion. Otherwise it let's you select a
completion from the popup list described above.

Completion of table names and column names is only active, if the forground
editor is connected to a database.


.. index::
   single: Editor; Splitting Statements

SQL Splitting
^^^^^^^^^^^^^

By default the editor tries to split it's content into separate SQL
statements. The beginning of a statement is marked with an arrow beside
the line numbers. You may receive better results when a connection is assigned
to the editor. When no connection is assigned the content of an editor is
treated as ANSI-SQL.

To disable query splitting either deactivate the appropriate option in
the preferences dialog to disable it globally or disable it opening the
popup menu in an editor and uncheck :guilabel:`SQL Splitting`.

When SQL splitting is activated each recognized SQL in the editor is
executed separately. Otherwise the whole content of the editor or the
selected text is executed as it were one statement.


.. index::
   single: Editor; Comments

Comment/Uncomment Lines
^^^^^^^^^^^^^^^^^^^^^^^

To comment or uncomment parts of a SQL statement either select
:menuselection:`Query --> Format --> Comment / Uncomment` or press
:kbd:`Ctrl+Shift+Space`. If no text is selected, the current line is commented
or uncommented. Otherwise all selected lines are toggled.


.. index::
   single: Editor; Formatting Statements

Format SQL Statements
^^^^^^^^^^^^^^^^^^^^^

To beautify the content of an editor or the selected text either select
:menuselection:`Query --> Format --> Format` or press
:kbd:`Ctrl+Shift+F`.

.. Note::
   This is an experimental feature. The results might differ from
   your expectations. ;-)
   Please file bug reports and feature request on the issue tracker
   for the :mod:`sqlparse` module at http://python-sqlparse.googlecode.com.


