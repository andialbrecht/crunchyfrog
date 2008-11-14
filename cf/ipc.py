# -*- coding: utf-8 -*-

import cPickle
import logging
import os
import socket
import SocketServer

import gobject
import gtk

from cf import IPC_SOCKET


class IPCRequestHandler(SocketServer.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.app = server.app
        SocketServer.BaseRequestHandler.__init__(self, request, client_address,
                                                 server)

    def _respond(self, value):
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
        data = self.request.recv(1024)
        logging.info('Received: %r' % data)
        cmd, args = data.split(':', 1)
        if cmd == 'ping':
            self._respond(True)
        elif cmd == 'new-instance':
            gobject.idle_add(lambda: not self.app.new_instance())
            self._respond(-1)
        elif cmd == 'get-instances':
            self._respond([(i.get_data('instance-id'), i.widget.get_title())
                           for i in self.app.get_instances()])
        elif cmd == 'open-uri':
            instance_id, uri = args.split(':', 1)
            for i in self.app.get_instances():
                if i.get_data('instance-id') == int(instance_id):
                    i.new_editor(uri)
                    self._respond(True)
            self._respond(False)
        else:
            self._respond('ERROR: Invalid command %r' % data)


class IPCListener(SocketServer.UnixStreamServer):

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

    def __init__(self):
        pass

    def communicate(self, msg):
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
        try:
            return self.communicate('get-instances:')
        except socket.error, err:
            return []

    def new_instance(self, args=None):
        try:
            return self.communicate('new-instance:')
        except socket.error, err:
            return None

    def open_uri(self, instance_id, uri):
        try:
            return self.communicate('open-uri:%d:%s' % (instance_id, uri))
        except socket.error, err:
            return False

    def ping(self):
        try:
            return self.communicate('ping:')
        except socket.error, err:
            return False


def get_client():
    client = IPCClient()
    return client
