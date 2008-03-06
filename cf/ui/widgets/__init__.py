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
import gnomevfs

import os

from kiwi.ui import dialogs

from gettext import gettext as _

from cf.backends import DBConnectError

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
        try:
            conn = datasource_info.dbconnect()
            self._editor.set_connection(conn)
            self.set_editor(self._editor)
        except DBConnectError, err:
            dialogs.error(_(u"Connection failed"), err.message)
        
    def on_set_connection(self, item, connection):
        self._editor.set_connection(connection)
        self.set_editor(self._editor)
        
    def rebuild_menu(self):
        while self._menu.get_children():
            self._menu.remove(self._menu.get_children()[0])
        if not self._editor:
            return
        ghas_connections = False
        dinfos = self.app.datasources.get_all()
        dinfos.sort(lambda x, y: cmp(x.get_label().lower(),
                                     y.get_label().lower()))
        for datasource_info in dinfos:
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
                 
class DataExportDialog(gtk.FileChooserDialog):
    
    def __init__(self, app, parent, data, selected, statement, description):
        gtk.FileChooserDialog.__init__(self, _(u"Export data"),
                                       parent,
                                       gtk.FILE_CHOOSER_ACTION_SAVE,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        self.data = data
        self.selected = selected
        self.statement = statement
        self.description = description
        self.app = app
        self._setup_widget()
        self._setup_connections()
        
    def _setup_widget(self):
        vbox = gtk.VBox()
        vbox.set_spacing(5)
        self.set_extra_widget(vbox)
        self.edit_export_options = gtk.CheckButton(_(u"_Edit export options"))
        vbox.pack_start(self.edit_export_options, False, False)
        self.export_selection = gtk.CheckButton(_(u"_Only export selected rows"))
        self.export_selection.set_sensitive(bool(self.selected))
        vbox.pack_start(self.export_selection, False, False)
        self.open_file = gtk.CheckButton(_(u"_Open file when finished"))
        vbox.pack_start(self.open_file, False, False)
        vbox.show_all()
        if self.app.config.get("editor.export.recent_folder"):
            self.set_current_folder(self.app.config.get("editor.export.recent_folder"))
        self._setup_filter()
    
    def _setup_filter(self):
        recent_filter = None
        for plugin in self.app.plugins.get_plugins("crunchyfrog.export", True):
            filter = gtk.FileFilter()
            filter.set_name(plugin.file_filter_name)
            for pattern in plugin.file_filter_pattern:
                filter.add_pattern(pattern)
            for mime in plugin.file_filter_mime:
                filter.add_mime_type(mime)
            self.add_filter(filter)
            filter.set_data("plugin", plugin)
            if self.app.config.get("editor.export.recent_filter", None) == plugin.id:
                recent_filter = filter
        if recent_filter:
            self.filter_changed(recent_filter)
        else:
            self.filter_changed(self.get_filter())
    
    def _setup_connections(self):
        self.connect("notify::filter", self.on_filter_changed)
        
    def on_filter_changed(self, dialog, param):
        gobject.idle_add(self.filter_changed, self.get_filter())
        
    def filter_changed(self, filter):
        plugin = filter.get_data("plugin")
        self.edit_export_options.set_sensitive(plugin.has_options)
        
    def export_data(self):
        self.app.config.set("editor.export.recent_folder", self.get_current_folder())
        plugin = self.get_filter().get_data("plugin")
        self.app.config.set("editor.export.recent_filter", plugin.id)
        if self.export_selection.get_property("sensitive") \
        and self.export_selection.get_active():
            rows = []
            for i in self.selected:
                rows.append(self.data[i])
        else:
            rows = self.data
        opts = {"filename" : self.get_filename(),
                "uri" : self.get_uri(),
                "query" : self.statement}
        if self.edit_export_options.get_property("sensitive") \
        and self.edit_export_options.get_active():
            opts.update(plugin.show_options(self.description, rows))
        plugin.export(self.description, rows, opts)
        if self.open_file.get_active():
            mime = gnomevfs.get_mime_type(opts["uri"])
            app_desc = gnomevfs.mime_get_default_application(mime)
            cmd = app_desc[2].split(" ")
            os.spawnvp(os.P_NOWAIT, cmd[0], cmd+[opts["uri"]])