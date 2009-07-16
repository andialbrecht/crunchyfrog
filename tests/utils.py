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

        sig_spec is a tuple (sender, signal_name, *args). Where args are the
        expected arguments to the callback.
        """
        sender = sig_spec[0]
        signal_name = sig_spec[1]
        sig_args = sig_spec[2:]
        cb_data = {'args': None, 'emitted': False}
        def _cb(s, *args):
            cb_data = args[-1]
            cb_data['args'] = args[:-1]
            cb_data['emitted'] = True
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
        self.assertEqual(cb_data['args'], sig_args)


class InstanceTest(AppTest):

    def setUp(self):
        super(InstanceTest, self).setUp()
        self.instance = self.app.new_instance()

    def tearDown(self):
        self.instance.destroy()
        self.instance = None
        super(InstanceTest, self).tearDown()
