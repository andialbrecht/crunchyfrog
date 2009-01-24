Configuring Data Sources
========================

Information on how to access data sources is stored in
:file:`<USER_DIR>/datasources.cfg`. The file is in a format readable and
writable by :mod:`ConfigParser`.

Each data source is represented by a section. The section name is used as
the identifier for a data source and therefore needs to be unique.


Allowed Options
---------------

password_store
   Tells the data source manager where the password is stored.
   Allowed values are ``config`` (the password is stored in plain text
   in this configuration file) and ``gnomekeyring`` (the password is
   stored in the Gnome key ring).

password (optional)
   The password to connect to this data source. This setting is only
   required if ``pasword_store`` is set tp ``config`` and if a password
   is required to connecto to the data source.


.. index::
   single: Data Source Manager

The data source informations are accessible through the data source manager.
An instance of the :class:`~cf.datasources.DatasourceManager` is
accessible through the :attr:`datasources` attribute of the application
object.

The :class:`~cf.datasources.DatasourceManger` provides the following
methods:

.. autoclass:: cf.datasources.DatasourceManager
   :members:
