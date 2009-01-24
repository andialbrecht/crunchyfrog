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
            if os.path.exists(path):
                print 'Removing generated documentation %s' % path
                shutil.rmtree(path)


clean.sub_commands.append(('clean_docs', None))
