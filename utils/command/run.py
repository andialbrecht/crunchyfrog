# -*- coding: utf-8 -*-

"""Command for running CrunchyFrog from local directory."""

import sys

from distutils.core import Command
from pkg_resources import load_entry_point


class run(Command):

    description = 'Launch CrunchyFrog from the local directory'
    user_options = [
        ('appargs=', None, 'Application arguments'),
        ]
    sub_commands = [('build', None)]

    def initialize_options(self):
        self.appargs = ''

    def finalize_options(self):
        pass

    def run(self):
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

        del sys.argv[1:]
        new_argv = [x for x in self.appargs.split(' ') if x]
        starter = load_entry_point(('crunchyfrog==%s'
                                    % (self.distribution.get_version(),)),
                                   'gui_scripts', 'crunchyfrog')
        starter(['crunchyfrog']+new_argv)
