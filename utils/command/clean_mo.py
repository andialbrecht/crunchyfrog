# -*- coding: utf-8 -*-

"""Cleanup .mo files."""

from distutils.command.clean import clean
from distutils.core import Command
import os


def _get_languages():
    for lang in os.listdir('po'):
        if lang.endswith('.pot') or lang[0] in ['.', '_']:
                continue
        yield lang

class clean_mo(Command):

    description = 'Clean up generated .mo files.'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for lang in _get_languages():
            mofile = os.path.join('po/%s/LC_MESSAGES/crunchyfrog.mo' % lang)
            if os.path.isfile(mofile):
                print 'cleaning %s' % mofile
                os.remove(mofile)


clean.sub_commands.append(('clean_mo', None))
