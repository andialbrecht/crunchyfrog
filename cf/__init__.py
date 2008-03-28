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
        http://cf.andialbrecht.de
    Additional documentation
        http://code.google.com/p/crunchyfrog/wiki/Documentation?tm=6
    Discussions
        http://groups.google.com/group/crunchyfrog

.. _GNOME: http://www.gnome.org
.. _Wiki: http://code.google.com/p/crunchyfrog/wiki/Documentation?tm=6
.. _CFApplication: cf.app.CFApplication.html
"""

__doc_all__ = ["main", "backends"]

import pygtk; pygtk.require("2.0")

import bonobo
import gnome
import gnomevfs
import gobject
import gtk
import gtk.glade
import gettext
import traceback
import os
import errno

gobject.threads_init()

from cf import release

from optparse import OptionParser
from os.path import abspath, dirname, join, isfile, isdir, expanduser
from os import makedirs
import sys

#if sys.version_info[:2] >= (2, 5):
#    LOG_FORMAT_APP = '[%(levelname)s] %(asctime)s %(message)s\n\t%(pathname)s:%(lineno)s in %(funcName)s\n\tPID: %(process)s, Thread: %(threadName)s [%(thread)d], Logger: %(name)s\n'
#else:
#    LOG_FORMAT_APP = '[%(levelname)s] %(asctime)s %(message)s\n\t%(pathname)s:%(lineno)s\n\tPID: %(process)s, Thread: %(threadName)s [%(thread)d], Logger: %(name)s\n'
LOG_FORMAT_APP = '%(levelname)s\t%(name)s\t%(created)f\t%(message)s'

import logging
logging.basicConfig(format=LOG_FORMAT_APP)

if isfile(abspath(join(dirname(__file__), "../setup.py"))):
    DATA_DIR = abspath(join(dirname(__file__), "../data"))
    LOCALE_DIR = abspath(join(dirname(__file__), "../po"))
else:
    from dist import DATA_DIR, LOCALE_DIR
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
USER_PLUGIN_REPO = join(USER_DIR, "repo.xml")
USER_PLUGIN_REPO_URI = gnomevfs.get_uri_from_local_path(USER_PLUGIN_REPO)
PID_FILE = join(USER_DIR, "crunchyfrog.pid")
    
gettext.bindtextdomain("crunchyfrog", LOCALE_DIR)
gettext.textdomain("crunchyfrog")
gtk.glade.bindtextdomain("crunchyfrog", LOCALE_DIR)
gtk.glade.textdomain("crunchyfrog")

from cf.app import CFApplication
from cf import dbus_manager

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

# grabbed from listen / gajm
def is_alive(pid_file):
    try:
        pf = open(pid_file)
    except:
        # probably file not found
        return False

    try:
        pid = int(pf.read().strip())
        pf.close()
    except:
        traceback.print_exc()
        # PID file exists, but something happened trying to read PID
        # Could be 0.10 style empty PID file, so assume Gajim is running
        return False

    try:
        if not os.path.exists('/proc'):
            print "missing /proc"
            return True # no /proc, assume Listen is running
        try:
            f = open('/proc/%d/cmdline'% pid) 
        except IOError, e:
            if e.errno == errno.ENOENT:
                return False # file/pid does not exist
            raise 

        n = f.read().lower()
        f.close()
        if n.find('cf/__init__.py') < 0:
            return False
        return True # Running Listen found at pid
    except:
        traceback.print_exc()

    # If we are here, pidfile exists, but some unexpected error occured.
    # Assume Listen is running.
    return True


def main():
    global FIRST_RUN
    options, args = _parse_commandline()
    options.first_run = not isfile(options.config)
    if options.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING
    logger = logging.getLogger()
    logger.setLevel(log_level)
    if not is_alive(PID_FILE):
        if isfile(abspath(join(dirname(__file__), "../setup.py"))):
            props = {'app-datadir': abspath(join(dirname(__file__), '../data'))}
        else:
            props = dict()
        gnome.init(release.name.lower(), release.version,
                   properties=props)       
        app = CFApplication(options)
        app.init()
        instance = app.new_instance(args)
        f = open(PID_FILE, "w")
        f.write(str(os.getpid()))
        f.close()
        logger.debug("PID: %d [%s]" % (os.getpid(), PID_FILE))
        for fname in args:
            instance.new_editor(fname)
        gtk.main()
        os.remove(PID_FILE)
    else:
        client = dbus_manager.get_client()
        if args:
            from cf.instance import InstanceSelector
            sel = InstanceSelector(client)
            if sel.run() == 1:
                instance_id = sel.get_instance_id()
                if not instance_id:
                    instance_id = client.new_instance()
                for fname in args:
                    client.open_uri(instance_id, fname)
            sel.destroy()
        else:
            client.new_instance()
            
        
if __name__ == "__main__":
    main()
