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

"""Simple UNIX socket server to handle multiple instances.

A very simple protocol is used:

 - Each request and response is a single line.
 - A request has the format 'cmd:[args]'
 - Response is a pickled Python value.
"""

import cPickle
import logging
import os
import socket
import SocketServer

import gobject
import gtk

from cf import IPC_SOCKET


class IPCRequestHandler(SocketServer.BaseRequestHandler):
    """RequestHandler: Talks to the application instance."""

    def __init__(self, request, client_address, server):
        self.app = server.app
        SocketServer.BaseRequestHandler.__init__(self, request, client_address,
                                                 server)

    def _respond(self, value):
        """Helper that converts the return value and sends it on the socket."""
        logging.info('Response: %r' % value)
        response = cPickle.dumps(value)
        assert len(response) <= 1024, 'Reponse too large'
        try:
            self.request.send(response)
        except socket.error, err:
            if err.args[0] == 32:  # Broken pipe
                pass
            else:
                raise

    def handle(self):
        """Handles a request."""
        data = self.request.recv(1024)
        logging.info('Received: %r' % data)
        cmd, args = data.split(':', 1)
        if cmd == 'ping':
            self._respond(True)
        elif cmd == 'new-instance':
            args = args.split('|')
            gobject.idle_add(lambda: not self.app.new_instance(args))
            self._respond(-1)
        elif cmd == 'get-instances':
            self._respond([(id(i), i.get_title())
                           for i in self.app.get_instances()])
        elif cmd == 'open-uri':
            instance_id, uri = args.split(':', 1)
            for i in self.app.get_instances():
                if id(i) == int(instance_id):
                    i.editor_create(uri)
                    self._respond(True)
            self._respond(False)
        else:
            self._respond('ERROR: Invalid command %r' % data)


class IPCListener(SocketServer.UnixStreamServer):
    """Simple server that listens on a UNIX socket."""

    def __init__(self, app):
        self.app = app
        self.address_family = socket.AF_UNIX
        self.socket_type = socket.SOCK_STREAM
        if os.path.exists(IPC_SOCKET):
            os.remove(IPC_SOCKET)
        SocketServer.UnixStreamServer.__init__(self, IPC_SOCKET,
                                               IPCRequestHandler)
        self.stay_alive = True

    def serve_forever(self):
        while self.stay_alive:
            self.handle_request()

    def shutdown(self):
        self.stay_alive = False
        try:
            os.remove(IPC_SOCKET)
        except OSError, err:
            if err.errno == 2:  # Socket is already gone.
                pass
            else:
                raise


class IPCClient(object):
    """Client."""

    def __init__(self):
        pass

    def communicate(self, msg):
        """Send message to listener and convert the pickled response."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(IPC_SOCKET)
        except socket.error, err:
            msg = 'Could not connect to IPC server on %r.' % IPC_SOCKET
            logging.info(msg)
            raise
        sock.send(msg)
        retval = sock.recv(1024)
        sock.close()
        try:
            retval = cPickle.loads(retval)
        except EOFError:
            retval = None
        return retval

    def get_instances(self):
        """Ask for active instances."""
        try:
            return self.communicate('get-instances:')
        except socket.error, err:
            return []

    def new_instance(self, args=None):
        """Creates a new instance, optionally with args as files to open."""
        if args is not None:
            args = '|'.join(args)
        else:
            args = ''
        try:
            return self.communicate('new-instance:%s' % args)
        except socket.error, err:
            return None

    def open_uri(self, instance_id, uri):
        """Opens a URI in an existing instance."""
        try:
            return self.communicate('open-uri:%d:%s' % (instance_id, uri))
        except socket.error, err:
            return False

    def ping(self):
        """Just say hello."""
        try:
            return self.communicate('ping:')
        except socket.error, err:
            return False


def get_client():
    """Return a client instance."""
    client = IPCClient()
    return client
