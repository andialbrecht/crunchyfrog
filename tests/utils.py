# -*- coding: utf-8 -*-

import __builtin__
import os
import unittest

import cf.application
import cf.cmdline
import cf.env


__builtin__.__dict__['_'] = lambda x: x


class AppTest(unittest.TestCase):

    def setUp(self):
        test_user_dir = os.path.join(os.path.dirname(__file__),
                                     '../testuserdir')
        opts, args = cf.cmdline.parser.parse_args(['testrunner',
                                                   '-u', test_user_dir])
        cf.env.init_environment(opts)
        self.app = cf.application.Application(opts)
