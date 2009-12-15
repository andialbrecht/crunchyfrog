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

"""Command line interface."""

import logging
import optparse
import os
import sys

import cf
from cf import release


def get_parser():
    """Creates and returns the command line parser."""
    usage = "usage: %prog [options] FILE1, FILE2, ..."
    parser = optparse.OptionParser(usage, prog=release.appname,
                                   version=release.version)
    parser.add_option("-c", "--config",
                      dest="config", default=cf.USER_CONF,
                      help="configuration file")
    group = parser.add_option_group('Logging options')
    group.add_option('-q', '--quiet', action='store_const', const=0,
                     dest='verbose', help='Print errors only.')
    group.add_option('-v', '--verbose', action='store_const', const=2,
                     dest='verbose', default=1,
                     help='Print info level logs (default).')
    group.add_option('--noisy', action='store_const', const=3,
                     dest='verbose', help='Print all logs.')
    return parser


def run():
    """Runs the application."""
    logging.basicConfig(format=('%(created)f %(levelname)s %(filename)s:'
                                '%(lineno)s %(message)s '))

    parser = get_parser()
    opts, args = parser.parse_args()

    if opts.verbose >= 3:
        logging.getLogger().setLevel(logging.DEBUG)
    elif opts.verbose >= 2:
        logging.getLogger().setLevel(logging.INFO)

    opts.first_run = not os.path.isfile(opts.config)

    try:
        from cf import ipc
        ipc_client = ipc.get_client()
    except AttributeError, err:
        logging.warning('No IPC available: %s', err)
        ipc_client = None

    # Let's import gtk and related.
    # Note: We import them here to allow command line usage
    # (e.g. crunchyfrog --version) without gkt requirements.
    try:
        import glib
        glib.set_application_name('CrunchyFrog')
    except ImportError:
        logging.debug('glib module not found.')

    import pygtk
    if not sys.platform == 'win32':
        pygtk.require('2.0')
    import gtk

    try:
        import gnome
        have_gnome = True
    except ImportError:
        have_gnome = False
    logging.info('GNOME enabled: %s', have_gnome and 'yes' or 'no')

    from cf.app import CFApplication

    # Check for running applications or create one
    if ipc_client is None or not ipc.is_alive(ipc_client):
        logging.info('Creating new application')
        if have_gnome:
            props = {}
            setup_py = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    '../setup.py'))
            if os.path.isfile(setup_py):
                props['app-datadir'] = cf.DATA_DIR
            props['human-readable-name'] = release.name
            gnome.init(release.name.lower(), release.version, properties=props)
        gtk.gdk.threads_init()
        gtk.gdk.threads_enter()
        app = CFApplication(opts)
        app.init()
        instance = app.new_instance(args)
        logging.info('Entering GTK main loop')
        gtk.main()
        logging.info('Leaving GTK main loop')
        gtk.gdk.threads_leave()

    # We have a running application, re-use it...
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

if __name__ == '__main__':
    run()