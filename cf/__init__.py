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

"""CrunchyFrog Package"""

import errno
import gettext
import hotshot
from optparse import OptionParser
import os
from os.path import abspath, dirname, join, isfile, isdir, expanduser
from os import makedirs
import sys
import traceback

import pygtk; pygtk.require("2.0")

# import kiwi first, just to get rid of no translation for domain message
import kiwi
import bonobo
import gnome
import gnomevfs
import gobject
import gtk
import gtk.glade

gobject.threads_init()

from cf import release


LOG_FORMAT_APP = '%(levelname)s\t%(name)s\t%(created)f\t%(message)s'

import logging
logging.basicConfig(format=LOG_FORMAT_APP)

try:
    from dist import DATA_DIR, LOCALE_DIR
except ImportError:
    DATA_DIR = abspath(join(dirname(__file__), "../data"))
    LOCALE_DIR = abspath(join(dirname(__file__), "../po"))

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
IPC_SOCKET = join(USER_DIR, "crunchyfog.sock")


gettext.bindtextdomain("crunchyfrog", LOCALE_DIR)
gettext.textdomain("crunchyfrog")
gtk.glade.bindtextdomain("crunchyfrog", LOCALE_DIR)
gtk.glade.textdomain("crunchyfrog")


from cf.app import CFApplication
from cf import ipc


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


def is_alive(client):
    response = client.ping()
    if not response:
        return False
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
    ipc_client = ipc.get_client()
    if not is_alive(ipc_client):
        logging.info('Creating new application')
        if isfile(abspath(join(dirname(__file__), "../setup.py"))):
            props = {'app-datadir':
                     abspath(join(dirname(__file__), '../data'))}
        else:
            props = dict()
        props['human-readable-name'] = release.name
        gnome.init(release.name.lower(), release.version,
                   properties=props)
        app = CFApplication(options)
        app.init()
        instance = app.new_instance(args)
        for fname in args:
            instance.new_editor(fname)
        gtk.main()
    else:
        logging.info('Running application found')
        if args:
            # TODO(andi): Move instance selector to app.
            #             - It causes broken pipes on socket.
            #             - If it's in app it can have a mainwin as parent.
            from cf.instance import InstanceSelector
            sel = InstanceSelector(ipc_client)
            if sel.run() == 1:
                instance_id = sel.get_instance_id()
                if not instance_id:
                    instance_id = ipc_client.new_instance()
                for fname in args:
                    ipc_client.open_uri(instance_id, fname)
            sel.destroy()
        else:
            ipc_client.new_instance()


if __name__ == "__main__":
    if "CF_PROFILE" in os.environ:
        prof = hotshot.Profile("crunchyfrog.prof")
        prof.runcall(main)
        prof.close()
    else:
        main()
