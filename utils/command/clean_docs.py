# -*- coding: utf-8 -*-

"""Cleanup generated documentation files."""

import os
import shutil
from distutils.command.clean import clean
from distutils.core import Command


class clean_docs(Command):

    description = 'Clean up generated documentation files.'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for path in ['docs/devguide/build', 'docs/manual/build']:
            print 'Cleaning %s' % path
            for item in os.listdir(path):
                if item == '.DUMMY':
                    continue
                shutil.rmtree(os.path.join(path, item))


clean.sub_commands.append(('clean_docs', None))
