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

"""Custom statusbar"""

import gtk
import pango


class CrunchyStatusbar(gtk.Statusbar):

    def __init__(self, app, instance):
        gtk.Statusbar.__init__(self)
        self.app = app
        self.instance = instance
        self.lbl_conn = gtk.Label()
        self.lbl_conn.set_alignment(0, 0.5)
        self.lbl_conn.set_ellipsize(pango.ELLIPSIZE_END)
        self.pack_start(self.lbl_conn)
        self.lbl_curpos = gtk.Label()
        self.lbl_curpos.set_alignment(0, 0.5)
        self.pack_start(self.lbl_curpos, False, False)
        self.lbl_insmode = gtk.Label()
        self.lbl_insmode.set_width_chars(3)
        self.pack_start(self.lbl_insmode, False, False)
