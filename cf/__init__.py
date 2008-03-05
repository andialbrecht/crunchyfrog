# -*- coding: utf-8 -*-

# crunchyfrog - a database schema browser and query tool
# Copyright (C) 2008 Andi Albrecht <albrecht.andi@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# $Id$

"""
CrunchyFrog Package

A good starting point to read this API documentation is the `CFApplication`_
class.


Other Resources
===============
    Development pages
        http://crunchyfrog.googlecode.com
    Additional documentation
        http://code.google.com/p/crunchyfrog/wiki/Documentation?tm=6
    Discussions
        http://groups.google.com/group/crunchyfrog

.. _GNOME: http://www.gnome.org
.. _Wiki: http://code.google.com/p/crunchyfrog/wiki/Documentation?tm=6
.. _CFApplication: cf.app.CFApplication.html
"""

__doc_all__ = ["main", "backends"]

import bonobo
import gnome
import gnomevfs
import gobject
import gtk
import gtk.glade
import gettext

from cf import release

from optparse import OptionParser
from os.path import abspath, dirname, join, isfile, isdir, expanduser
from os import makedirs
import sys
import logging

if isfile(abspath(join(dirname(__file__), "../setup.py"))):
    DATA_DIR = abspath(join(dirname(__file__), "../data"))
    LOCALE_DIR = abspath(join(dirname(__file__), "../po"))
else:
    root = abspath(join(dirname(sys.argv[0]), "../"))
    DATA_DIR = join(root, "share", release.appname)
    LOCALE_DIR = join(root, "share", "locale")
PLUGIN_DIR = join(DATA_DIR, "plugins")
USER_CONFIG_DIR = abspath(expanduser("~/.config/crunchyfrog"))
USER_CONF = join(USER_CONFIG_DIR, "config")
if not isdir(USER_CONFIG_DIR):
    makedirs(USER_CONFIG_DIR)
USER_DIR = abspath(expanduser("~/.crunchyfrog"))
if not isdir(USER_DIR):
    makedirs(USER_DIR)
USER_PLUGIN_DIR = join(USER_DIR, "plugins/")
if not isdir(USER_PLUGIN_DIR):
    makedirs(USER_PLUGIN_DIR)
USER_PLUGIN_URI = gnomevfs.get_uri_from_local_path(USER_PLUGIN_DIR)
    
gettext.bindtextdomain("crunchyfrog", LOCALE_DIR)
gettext.textdomain("crunchyfrog")
gtk.glade.bindtextdomain("crunchyfrog", LOCALE_DIR)
gtk.glade.textdomain("crunchyfrog")

if sys.version_info[:2] >= (2, 5):
    LOG_FORMAT_APP = '[%(levelname)s] %(message)s\n\t%(pathname)s:%(lineno)s in %(funcName)s\n\tPID: %(process)s, Thread: %(threadName)s [%(thread)d]\n'
else:
    LOG_FORMAT_APP = '[%(levelname)s] %(message)s\n\t%(pathname)s:%(lineno)s\n\tPID: %(process)s, Thread: %(threadName)s [%(thread)d]\n'


from cf.app import CFApplication

def new_instance_cb(xapp, argc, argv):
    from cf.instance import CFInstance
    app = CFInstance(xapp)
    app._init_ui(argv)
    l = xapp.get_data("instances")
    l.append(app)
    xapp.set_data("instances", l)
    for item in argv:
        app.new_editor(item)
    app.widget.show_all()
    app.widget.connect("destroy", ui_destroy_cb, app, xapp)
    xapp.cb.emit("instance-created", app)
    return argc

def ui_destroy_cb(widget, app, xapp):
    l = xapp.get_data("instances")
    if app in l:
        l.remove(app)
    xapp.set_data("instances", l)
    if not l:
        xapp.shutdown()
        bonobo.main_quit()

def _parse_commandline():
    """Parses command line arguments and handles all arguments
    which exit immediately (e.g. --version)"""
    usage = "usage: %prog [options] FILE1, FILE2, ..."
    parser = OptionParser(usage)
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug",
                      default=False,
                      help="run in debug mode")
    parser.add_option("--version",
                      action="store_true", dest="show_version",
                      default=False,
                      help="show program's version number and exit")
    parser.add_option("-c", "--config",
                      dest="config", default=USER_CONF,
                      help="configuration file")
    options, args = parser.parse_args()
    if options.show_version:
        print "%s - %s" % (release.name, release.description)
        print "Version %s" % release.version
        print
        sys.exit()
    return options, args

def main():
    options, args = _parse_commandline()
    if options.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING
    logging.basicConfig(format=LOG_FORMAT_APP,
                        level=log_level)
    bonobo.activate()
    app = CFApplication(options)
    client = app.register_unique(app.create_serverinfo(("LANG",)))
    if not client:
        if isfile(abspath(join(dirname(__file__), "../setup.py"))):
            props = {'app-datadir': abspath(join(dirname(__file__), '../data'))}
        else:
            props = dict()
        gnome.init(release.name.lower(), release.version,
                   properties=props)
        app.connect("new-instance", new_instance_cb)
        app.set_data("instances", list())
        app.new_instance(args)
        gobject.threads_init()
        gtk.gdk.threads_init()
        bonobo.main()
        app.unref()
    else:
        client.new_instance(args)
        
if __name__ == "__main__":
    main()