# -*- coding: utf-8 -*-

"""build_mo command to compile gettext catalogs."""

from distutils.command.build import build
from distutils.core import Command
import subprocess
import sys

class build_mo(Command):

    description = 'Compile message catalogs'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        proc = subprocess.Popen(['make', 'msg-compile'])
        proc.wait()
        if proc.returncode:
            print 'Failed to compile message catalogs.'
            sys.exit(1)

build.sub_commands.append(('build_mo', None))
