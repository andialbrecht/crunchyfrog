# -*- coding: utf-8 -*-

"""build_api command -- Generate API docs from sources"""

from distutils.command.build import build
from distutils.core import Command
import os

from utils import genapi


class build_api(Command):

    description = 'Generate API docs from sources.'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        genapi.main()

build.sub_commands.append(('build_api', None))
