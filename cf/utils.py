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

# $Id$

"""Nifty little helpers"""

import re

import gtk
import gobject

# found here: http://www.mail-archive.com/pygtk@daa.com.au/msg12556.html
def Emit(obj, *args):

    def Do_Emit(obj, sig, *args):
        gtk.gdk.threads_enter()
        obj.emit(sig, *args)
        gtk.gdk.threads_leave()
        return False
    gobject.idle_add(Do_Emit, obj, *args, **{"priority" : gobject.PRIORITY_HIGH})
#END: Emit

def normalize_sql(sql):
    """Removes duplicated whitespaces and line breaks."""
    p = re.compile(r'\s+', re.MULTILINE)
    return p.sub(' ', sql)
