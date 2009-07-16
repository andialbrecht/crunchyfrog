# -*- coding: utf-8 -*-

import __builtin__
import os
import unittest
import time

import gtk

import cf.app
import cf.cmdline
#import cf.env


__builtin__.__dict__['_'] = lambda x: x

# Monkey patch gtk.main_quit() to avoid RuntimeError. We're never in the
# mainloop here.
gtk.main_quit = lambda *a: None


class AppTest(unittest.TestCase):

    def setUp(self):
        test_user_dir = os.path.join(os.path.dirname(__file__),
                                     '../testuserdir')
        parser = cf.cmdline.get_parser()
        opts, args = parser.parse_args(['testrunner'])
        opts.first_run = False
        self.app = cf.app.CFApplication(opts)
        self.app.init()

    def refresh_gui(self, delay=0):
        # see http://unpythonic.blogspot.com/2007/03/unit-testing-pygtk.html
        while gtk.events_pending():
            gtk.main_iteration_do(block=False)
        time.sleep(delay)

    def assertEmitted(self, sig_spec, func, *args, **kwargs):
        """Assert that a signal was emitted.

        sig_spec is a tuple (sender, signal_name, callback=None).
        If callback is given, it is used as a signal callback.
        """
        sender = sig_spec[0]
        signal_name = sig_spec[1]
        if len(sig_spec) == 3:
            sig_cb = sig_spec[2]
        else:
            sig_cb = None
        cb_data = {'emitted': False, 'sig_cb': sig_cb}
        def _cb(s, *args):
            cb_data = args[-1]
            cb_data['emitted'] = True
            sig_cb = cb_data['sig_cb']
            if sig_cb is not None:
                sig_cb(s, *args)
        try:
            sender.connect(signal_name, _cb, cb_data)
        except Exception, err:
            raise AssertionError(('Failed to connect %r on object %r: %s'
                                  % (signal_name, sender, err)))
        try:
            func(*args, **kwargs)
        except Exception, err:
            raise AssertionError(('Function call failed: %s' % err))
        self.refresh_gui()
        self.assert_(cb_data['emitted'], 'Signal %r not emitted' % signal_name)


class InstanceTest(AppTest):

    def setUp(self):
        super(InstanceTest, self).setUp()
        self.instance = self.app.new_instance()

    def tearDown(self):
        self.instance.destroy()
        self.instance = None
        super(InstanceTest, self).tearDown()
