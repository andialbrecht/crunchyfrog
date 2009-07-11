Writing Plugins
===============

.. autoclass:: cf.plugins.Plugin
   :members:

Special Plugin Classes
----------------------

.. autoclass:: cf.plugins.ExportPlugin
   :members:



Entry points
------------

``crunchyfrog.plugin``
  Generic entry point

``crunchyfrog.backends``
  A database backend

``crunchyfrog.export``
  Export filter

``crunchyfrog.editor``
  SQL editor add on


Meta Data
---------

Usually you there's no need to define additional meta data besides that
already defined in :file:`setup.py` of your plugin.
