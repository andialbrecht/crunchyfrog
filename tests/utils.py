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


class InstanceTest(AppTest):

    def setUp(self):
        super(InstanceTest, self).setUp()
        self.instance = self.app.new_instance()

    def tearDown(self):
        self.instance.destroy()
        self.instance = None
        super(InstanceTest, self).tearDown()
