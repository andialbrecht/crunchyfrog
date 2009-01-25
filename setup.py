#!/usr/bin/env python
# -*- coding: utf-8 -*-

# crunchyfrog - a database schema browser and query tool
# Copyright (C) 2008 Andi Albrecht <albrecht.andi@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from distutils.command.build import build
from distutils.command.clean import clean
from distutils.core import setup
from glob import glob
import os
import shutil
import sys

from utils.command.build_api import build_api
from utils.command.clean_mo import clean_mo
from utils.command.clean_docs import clean_docs
from utils.command.clean_mo import compile_mo


from cf import release


class clean_with_subcommands(clean):

    def run(self):
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)
        clean.run(self)


CMD_CLASS = {
    'compile_catalog': compile_mo,
    'clean': clean_with_subcommands,
    'clean_mo': clean_mo,
    'compile_mo': compile_mo,
    'clean_docs': clean_docs,
    'build_api': build_api,
}


# compile_mo: We're using a msgfmt.py based compile to have no Babel dependency
#   on buildbot like launchpad.net...
#   So, all babel commands are optional...
try:
    from babel.messages import frontend as babel
    CMD_CLASS['extract_messages'] = babel.extract_messages
    CMD_CLASS['init_catalog'] = babel.init_catalog
    CMD_CLASS['udpate_catalog'] = babel.update_catalog
except ImportError:
    pass

# The same for the documentation. Currently it's not distributed, so
#   Sphinx is optional and not needed on buildbots.
try:
    from sphinx.setup_command import BuildDoc
    CMD_CLASS['build_devguide'] = BuildDoc
except ImportError:
    pass


DATA_FILES = []

# Glade
DATA_FILES += [('share/crunchyfrog/glade', glob('data/glade/*.glade'))]

# Plugins
DATA_FILES += [('share/crunchyfrog/plugins', [])]

# Pixmaps
DATA_FILES += [('share/crunchyfrog/pixmaps', glob('data/pixmaps/*.png'))]

# Data
DATA_FILES += [('share/applications', ['data/crunchyfrog.desktop'])]
DATA_FILES += [('share/icons/hicolor/scalable/apps', ['data/crunchyfrog.svg'])]
DATA_FILES += [('share/pixmaps', ['data/crunchyfrog.svg'])]
DATA_FILES += [('share/icons/hicolor/24x24/apps', ['data/crunchyfrog.png'])]

# Manpage
DATA_FILES += [('share/man/man1', ['data/crunchyfrog.1'])]

# Documentation
#DATA_FILES += [('share/docs/crunchyfrog/devguide',
#                glob('docs/devguide/build/html/*.*'))]

# Locales
for lang in os.listdir('po/'):
    path = os.path.join('po/', lang)
    if not os.path.isdir(path) or lang[0] in ['.', '_']:
        continue
    DATA_FILES += [('share/locale/%s/LC_MESSAGES' % lang,
                    ['po/%s/LC_MESSAGES/crunchyfrog.mo' % lang])]


setup(
    name=release.appname,
    version=release.version,
    description=release.description,
    author=release.author,
    author_email=release.author_email,
    long_description=release.long_description,
    license='GPL',
    url=release.url,
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: Gnome",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Topic :: Database :: Front-Ends",
        "Topic :: Desktop Environment :: Gnome",
    ],
    packages=['cf', 'cf/backends', 'cf/backends/schema',
              'cf/config', 'cf/filter', 'cf/plugins',
              'cf/shell', 'cf/sqlparse', 'cf/thirdparty',
              'cf/ui', 'cf/ui/widgets', 'cf/ui/widgets/sqlview'],
    package_data={'cf': ['config/default.cfg']},
    scripts=['crunchyfrog'],
    data_files=DATA_FILES,
    cmdclass=CMD_CLASS,
)
