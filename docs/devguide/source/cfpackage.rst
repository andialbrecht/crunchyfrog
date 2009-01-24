The CrunchyFrog Package
=======================


Environment
^^^^^^^^^^^

The :mod:`~cf.env` holds information about the environment the application
runs in. It defines the following paths:

:const:`DATA_DIR`
  Path to the base directory for application's data files
  (e.g. :file:`/usr/share/crunchyfrog`).

:const:`PLUGIN_DIR`
  Path to system-wide plugin directory (e.g. :file:`<DATA_DIR>/plugins`)

:const:`GLADE_DIR`
  Path to Glade files (e.g. :file:`<DATA_DIR>/glade`)

:const:`LOCALE_DIR`
  Path to locales directory (e.g. :file:`/usr/share/locales/`)

When the application is run from a source checkout :const:`DATA_DIR` and
:const:`LOCALE_DIR` are pointing to the corresponding directories in checkout
directory.
When :file:`../setup.py` is not present a system-wide install is assumed and
the paths are set accordingly.

.. index::
   single: Packaging; Setting distribution-specific paths

Packagers can modify :file:`cf/env.py` according to distribution specifc
requirements.



Application start
^^^^^^^^^^^^^^^^^
* command line options
* init of logging and gettext
* application init

