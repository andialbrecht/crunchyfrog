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
import logging
from optparse import OptionParser
import os
from os.path import abspath, dirname, join, isfile, isdir, expanduser
from os import makedirs
import sys
import traceback

import pygtk; pygtk.require("2.0")

import gobject
import gtk
import gtk.glade

try:
    import gnome
    HAVE_GNOME = True
except ImportError:
    HAVE_GNOME = False

gobject.threads_init()

from cf import release


PREFIX = '/usr/'

if os.path.exists(os.path.join(os.path.dirname(__file__), '../setup.py')):
    DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/')
    LOCALE_DIR = os.path.join(os.path.dirname(__file__), '../po/')
else:
    DATA_DIR = os.path.join(PREFIX, 'share/crunchyfrog/')
    LOCALE_DIR = os.path.join(PREFIX, 'share/locale/')

DATA_DIR = os.path.abspath(DATA_DIR)
LOCALE_DIR = os.path.abspath(LOCALE_DIR)


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
USER_PLUGIN_REPO = join(USER_DIR, "repo.xml")
IPC_SOCKET = join(USER_DIR, "crunchyfog.sock")


#gettext.bindtextdomain("crunchyfrog", LOCALE_DIR)
#gettext.textdomain("crunchyfrog")
gtk.glade.bindtextdomain("crunchyfrog", LOCALE_DIR)
gtk.glade.textdomain("crunchyfrog")
gettext.install('crunchyfrog', LOCALE_DIR, True)


from cf.app import CFApplication


def _parse_commandline():
    """Parses command line arguments and handles all arguments
    which exit immediately (e.g. --version)"""
    usage = "usage: %prog [options] FILE1, FILE2, ..."
    parser = OptionParser(usage, prog=release.appname, version=release.version)
    parser.add_option("-c", "--config",
                      dest="config", default=USER_CONF,
                      help="configuration file")
    group = parser.add_option_group('Logging options')
    group.add_option('-q', '--quiet', action='store_const', const=0,
                     dest='verbose', help='Print errors only.')
    group.add_option('-v', '--verbose', action='store_const', const=2,
                     dest='verbose', default=1,
                     help='Print info level logs (default).')
    group.add_option('--noisy', action='store_const', const=3,
                     dest='verbose', help='Print all logs.')
    options, args = parser.parse_args()
    return options, args


def is_alive(client):
    response = client.ping()
    if not response:
        return False
    return True


def main():
    global FIRST_RUN
    logging.basicConfig(format=('%(asctime).19s %(levelname)s %(filename)s:'
                                '%(lineno)s %(message)s '))
    options, args = _parse_commandline()
    options.first_run = not isfile(options.config)
    if options.verbose >= 3:
        logging.getLogger().setLevel(logging.DEBUG)
    elif options.verbose >= 2:
        logging.getLogger().setLevel(logging.INFO)
    try:
        from cf import ipc
        ipc_client = ipc.get_client()
    except AttributeError, err:
        logging.warning('No IPC available: %s', err)
        ipc_client = None
    if ipc_client is None or not is_alive(ipc_client):
        logging.info('Creating new application')
        if HAVE_GNOME:
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
                    instance_id = ipc_client.new_instance(args)
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
