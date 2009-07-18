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

"""UI helper functions."""

import os

import gtk

from cf import DATA_DIR


def get_logo_icon_list():
    """Returns a list of pixbufs for use with gtk.Window.set_icon_list()."""
    return tuple(get_logo_icon(size) for size in [24, 48, 96, 256])

def get_logo_icon(size):
    """Returns a pixbuf with the logo."""
    icon_dir = os.path.join(DATA_DIR, 'pixmaps/')
    fname = 'crunchyfrog_%dx%d.png' % (size, size)
    return gtk.gdk.pixbuf_new_from_file(os.path.join(icon_dir, fname))
