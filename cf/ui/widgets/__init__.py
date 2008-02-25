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

"""Shared widgets"""

import gtk
import gobject
import gdl
import pango

from gettext import gettext as _

class ConnectionButton(gdl.ComboButton):
    
    def __init__(self, app):
        gdl.ComboButton.__init__(self)
        self.app = app
        self._setup_widget()
        self.set_editor(None)
        self.app.datasources.connect("datasource-modified", self.on_datasource_modified)
        
    def _setup_widget(self):
        lbl = self.get_children()[0].get_children()[0].get_children()[0].get_children()[1]
        lbl.set_max_width_chars(25)
        lbl.set_ellipsize(pango.ELLIPSIZE_END)
        lbl.set_use_markup(True)
        self.label = lbl
        self._menu = gtk.Menu()
        self.set_menu(self._menu)
        
    def on_datasource_modified(self, *args):
        self.rebuild_menu()
        
    def on_new_connection(self, item, datasource_info):
        conn = datasource_info.dbconnect()
        self._editor.set_connection(conn)
        self.set_editor(self._editor)
        
    def on_set_connection(self, item, connection):
        self._editor.set_connection(connection)
        self.set_editor(self._editor)
        
    def rebuild_menu(self):
        while self._menu.get_children():
            self._menu.remove(self._menu.get_children()[0])
        if not self._editor:
            return
        ghas_connections = False
        for datasource_info in self.app.datasources.get_all():
            item = gtk.MenuItem(datasource_info.get_label())
            item.show()
            self._menu.append(item)
            menu = gtk.Menu()
            has_connections = False
            for conn in datasource_info.get_connections():
                yitem = gtk.MenuItem(_(u"Connection")+" #%s" % conn.conn_number)
                yitem.connect("activate", self.on_set_connection, conn)
                yitem.show()
                menu.append(yitem)
                has_connections = True
                ghas_connections = True
            if has_connections:
                sep = gtk.SeparatorMenuItem()
                sep.show()
                menu.append(sep)
            xitem = gtk.MenuItem(_(u"New connection"))
            xitem.connect("activate", self.on_new_connection, datasource_info)
            xitem.show()
            menu.append(xitem)
            item.set_submenu(menu)
        sep = gtk.SeparatorMenuItem()
        sep.show()
        self._menu.append(sep)
        item = gtk.MenuItem(_(u"Manage open connections"))
        item.set_sensitive(ghas_connections)
        item.show()
        self._menu.append(item)    
        
    def set_editor(self, editor):
        self._editor = editor
        self.set_sensitive(bool(editor))
        self.rebuild_menu()
        if editor:
            if editor.connection:
                self.set_label(editor.connection.get_label())
                markup = "<b>"+editor.connection.datasource_info.get_label()+"</b>\n"
                markup += _(u"Connection")+" #%s" % editor.connection.conn_number
                self.set_tooltip_markup(markup)
            else:
                self.set_label("<"+_(u"Not connected")+">")
                self.set_tooltip_markup(_(u"Click to open a connection"))
                 