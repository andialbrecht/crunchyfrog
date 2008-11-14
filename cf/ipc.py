# -*- coding: utf-8 -*-

import cPickle
import logging
import os
import socket
import SocketServer

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
        self.request.send(response)

    def handle(self):
        data = self.request.recv(1024)
        logging.info('Received: %r' % data)
        cmd, args = data.split(':')
        if cmd == 'ping':
            self._respond(True)
        elif cmd == 'new-instance':
            instance = self.app.new_instance()
            self._respond(instance.get_data('instance-id'))
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
        retval = cPickle.loads(retval)
        return retval

    def get_instances(self):
        pass

    def new_instance(self, args=None):
        print 'ARGS', args
        try:
            return self.communicate('new-instance:')
        except socket.error, err:
            return None

    def ping(self):
        try:
            return self.communicate('ping:')
        except socket.error, err:
            return False


def get_client():
    client = IPCClient()
    return client
