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

try:
    # Try to import the original one first (Sphinx >= 0.5)
    from sphinx.setup_command import BuildDoc
except ImportError:
    # ok, it failed... try the local copy
    from utils.command.sphinx_build import BuildDoc

from utils.command.build_api import build_api
from utils.command.build_manpage import build_manpage
from utils.command.build_mo import build_mo
from utils.command.clean_docs import clean_docs
from utils.command.clean_mo import clean_mo


from cf import release


def find_packages(base):
    ret = [base]
    for path in os.listdir(base):
        full_path = os.path.join(base, path)
        if os.path.isdir(full_path):
            ret += find_packages(full_path)
    return ret


class clean_with_subcommands(clean):

    def run(self):
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)
        clean.run(self)


CMD_CLASS = {
    'clean': clean_with_subcommands,
    'clean_docs': clean_docs,
    'build_api': build_api,
    'build_devguide': BuildDoc,
    'build_manual': BuildDoc,
    'build_manpage': build_manpage,
    'build_mo': build_mo,
    'clean_mo': clean_mo,
}


build.sub_commands.append(('build_manual', None))


DATA_FILES = []

# Glade
DATA_FILES += [('share/crunchyfrog/glade', glob('data/glade/*.glade'))]

# Plugins
# Expects that each directory in data/plugins is a plugin and that
# the plugin directories contain Python files only.
for dirname in os.listdir('data/plugins'):
    if dirname[0] in ('.', '_'):
        continue
    DATA_FILES += [(os.path.join('share/crunchyfrog/plugins', dirname),
                    glob(os.path.join('data/plugins', dirname, '*.py')))]

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
DATA_FILES += [('share/doc/crunchyfrog', ['README', 'CHANGES', 'COPYING'])]
DATA_FILES += [('share/doc/crunchyfrog/manual',
                glob('docs/manual/build/html/*.*')),
               ('share/doc/crunchyfrog/manual/_images',
                glob('docs/manual/build/html/_images/*.*')),
               ('share/doc/crunchyfrog/manual/_sources',
                glob('docs/manual/build/html/_sources/*.*')),
               ('share/doc/crunchyfrog/manual/_static',
                glob('docs/manual/build/html/_static/*.*'))]

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
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'Environment :: X11 Applications :: Gnome',
        'Environment :: MacOS X',
        'Environment :: Win32 (MS Windows)',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database :: Front-Ends',
    ],
    packages=find_packages('cf'),
    package_data={'cf': ['config/default.cfg']},
    scripts=['crunchyfrog'],
    data_files=DATA_FILES,
    cmdclass=CMD_CLASS,
)
