# -*- coding: utf-8 -*-

"""build_mo command to compile gettext catalogs."""

from distutils.command.build import build
from distutils.core import Command

import os
import sys

from utils import msgfmt

PO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       '../../po'))


class build_mo(Command):

    description = 'Compile message catalogs'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def _generate(self, lang):
        infile = os.path.join(PO_PATH, lang, 'LC_MESSAGES', 'crunchyfrog.po')
        outfile = os.path.join(PO_PATH, lang, 'LC_MESSAGES', 'crunchyfrog.mo')
        msgfmt.make(infile, outfile)

    def run(self):
        for path in os.listdir(PO_PATH):
            if os.path.isdir(os.path.join(PO_PATH, path)):
                self._generate(path)


build.sub_commands.append(('build_mo', None))
