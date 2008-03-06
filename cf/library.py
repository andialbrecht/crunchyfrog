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

"""SQL library

This module contains the SQL library plugin.

:ToDo's:
    - Management interface (reorder, delete, rename, edit, export, dump, ...)
"""

import gtk
import gobject

from cf.plugins.core import GenericPlugin
from cf.plugins.mixins import MenubarMixin, EditorMixin, UserDBMixin
from cf.ui import GladeWidget

from gettext import gettext as _

class SQLLibraryPlugin(GenericPlugin, MenubarMixin, EditorMixin,
                       UserDBMixin):
    """SQL library plugin"""
    name = _(u"Library")
    description = _(u"A personal SQL library")
    icon = "gnome-terminal"
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://crunchyfrog.googlecode.com"
    version = "0.1"
    
    def __init__(self, app):
        GenericPlugin.__init__(self, app)
        self._mn_add = dict()
        self._menu_items = dict()
        
    def on_add_to_library(self, menuitem, instance):
        editor = instance.get_editor()
        if not editor:
            return
        buffer = editor.textview.get_buffer()
        txt = buffer.get_text(*buffer.get_bounds())
        self.add_to_library(txt)
        
    def on_load_from_library(self, menuitem, id_, instance):
        editor = instance.get_editor()
        if not editor:
            editor = instance.new_editor()
        sql = "select statement from sqllib_sql where id = %s" % id_
        self.userdb.cursor.execute(sql)
        editor.textview.get_buffer().set_text(self.userdb.cursor.fetchone()[0])
        
    def add_to_library(self, txt):
        dlg = LibSaveDialog(self.app)
        dlg.set_statement(txt)
        if dlg.run():
            name = dlg.xml.get_widget("libsave_name").get_text().strip()
            description = dlg.xml.get_widget("libsave_description").get_text().strip() or None
            cat = dlg.get_category()
            sql = "insert into sqllib_sql (title, description, statement, category) values (?, ?, ?, ?);"
            self.userdb.cursor.execute(sql, (name, description, txt, cat))
            self.userdb.conn.commit()
            gobject.idle_add(self.rebuild_menues)
        dlg.destroy()
        
    def menubar_load(self, menubar, instance):
        children = menubar.get_children()
        pos = -1
        for i in range(len(children)):
            if children[i].get_name() == "mn_help":
                pos = i
                break
        item = gtk.MenuItem(_(u"_Library"))
        item.set_name("library")
        item.show()
        menubar.insert(item, pos)
        menu = gtk.Menu()
        item.set_submenu(menu)
        item = gtk.SeparatorMenuItem()
        item.show()
        menu.append(item)
        self._menu_items[instance] = menu
        item = gtk.MenuItem(_(u"_Add to library"))
        item.set_sensitive(False)
        item.show()
        menu.append(item)
        item.connect("activate", self.on_add_to_library, instance)
        self._mn_add[instance] = item
        self.rebuild_menues()
        
    def menubar_unload(self, menubar, instance):
        for item in menubar.get_children():
            if item.get_name() == "library":
                menubar.remove(item)
                return
        del self._menu_items[instance]
        del self._mn_add[instance]
            
    def set_editor(self, editor, instance):
        self._mn_add[instance].set_sensitive(bool(editor))
        
    def userdb_init(self):
        if self.userdb.get_table_version("sqllib_cat") == None:
            self.userdb.create_table("sqllib_cat", "0.1", TABLE_LIB_CAT)
        if self.userdb.get_table_version("sqllib_sql") == None:
            self.userdb.create_table("sqllib_sql", "0.1", TABLE_LIB_SQL)
            
    def rebuild_menues(self):
        def add_items(mitem, parent, instance):
            sql = "select id, name from sqllib_cat where "
            if parent:
                sql += "parent = %s" % parent
            else:
                sql += "parent is null"
            sql += " order by name"
            self.userdb.cursor.execute(sql)
            pos = 0
            for entry in self.userdb.cursor.fetchall():
                item = gtk.ImageMenuItem(gtk.STOCK_OPEN)
                item.get_children()[0].set_label(entry[1])
                item.show()
                smenu = gtk.Menu()
                item.set_submenu(smenu)
                add_items(smenu, entry[0], instance)
                mitem.insert(item, pos)
                pos += 1
            sql = "select id, title from sqllib_sql where "
            if parent:
                sql += "category = %s" % parent
            else:
                sql += "category is null"
            self.userdb.cursor.execute(sql)
            for entry in self.userdb.cursor.fetchall():
                item = gtk.ImageMenuItem(gtk.STOCK_JUSTIFY_LEFT)
                item.get_children()[0].set_label(entry[1])
                item.connect("activate", self.on_load_from_library, entry[0], instance)
                item.show()
                mitem.insert(item, pos)
                pos += 1
        for instance, menuitem in self._menu_items.items():
            while menuitem.get_children():
                child = menuitem.get_children()[0]
                if isinstance(child, gtk.SeparatorMenuItem):
                    break
                menuitem.remove(child)
            add_items(menuitem, None, instance)
            
class LibSaveDialog(GladeWidget):
    """Save statement to library dialog"""
    
    def __init__(self, app):
        GladeWidget.__init__(self, app, "crunchyfrog", "sqllib_save")
        self.init_categories()
        
    def _setup_widget(self):
        model = gtk.TreeStore(int, str)
        treeview = self.xml.get_widget("libsave_category")
        treeview.set_model(model)
        self.cat_model = model
        renderer = gtk.CellRendererText()
        renderer.connect("edited", self.on_cat_edited)
        renderer.set_property("editable", True)
        col = gtk.TreeViewColumn("", renderer, text=1)
        treeview.append_column(col)
        treeview.connect("button-press-event", self.on_button_press_event)
        
    def on_add_category(self, menuitem, parent):
        iter = self.cat_model.append(parent)
        sql = "insert into sqllib_cat (name, parent) values (?, ?)"
        if parent:
            parent_id = self.cat_model.get_value(parent, 0)
        else:
            parent_id = None
        name = _(u"New category")
        self.app.userdb.cursor.execute(sql, (name, parent_id))
        id = self.app.userdb.cursor.lastrowid
        self.app.userdb.connection.commit()
        self.cat_model.set(iter, 0, id, 1, name)
        
    def on_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            popup = gtk.Menu()
            pthinfo = treeview.get_path_at_pos(x, y)
            parent = None
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                model = treeview.get_model()
                parent = model.iter_parent(model.get_iter(path))
            item = gtk.MenuItem(_(u"Add category"))
            item.show()
            item.connect("activate", self.on_add_category, parent)
            popup.append(item)
            popup.show_all()
            popup.popup( None, None, None, event.button, time)
            return 1
        
    def on_cat_edited(self, renderer, path, value):
        iter = self.cat_model.get_iter(path)
        self.cat_model.set_value(iter, 1, value)
        sql = "update sqllib_cat set name = ? where id = ?"
        self.app.userdb.cursor.execute(sql, (value, self.cat_model.get_value(iter, 0)))
        self.app.userdb.connection.commit()
        
    def on_name_changed(self, *args):
        txt = self.xml.get_widget("libsave_name").get_text().strip()
        self.xml.get_widget("libsave_btn_save").set_sensitive(bool(txt))
        
    def init_categories(self, parent=None):
        sql = "select id, name from sqllib_cat"
        if parent:
            parent_id = self.cat_model.get_value(parent, 0)
            sql += " where parent = %s" % parent_id
        else:
            sql += " where parent is null"
        sql += " order by name"
        self.app.userdb.cursor.execute(sql)
        for item in self.app.userdb.cursor.fetchall():
            iter = self.cat_model.append(parent)
            self.cat_model.set(iter, 0, item[0], 1, item[1])
            sql = "select count(*) from sqllib_cat where parent = %s" % item[0]
            self.app.userdb.cursor.execute(sql)
            if self.app.userdb.cursor.fetchone()[0]:
                self.init_categories(iter)
        
    def set_statement(self, statement):
        buffer = self.xml.get_widget("libsave_statement").get_buffer()
        buffer.set_text(statement)
        
    def get_category(self):
        sel = self.xml.get_widget("libsave_category").get_selection()
        model, iter = sel.get_selected()
        if iter:
            return model.get_value(iter, 0)
        else:
            return None
            
            
TABLE_LIB_CAT = """create table sqllib_cat (
    id integer primary key not null,
    name text,
    parent integer references sqllib_cat
);"""

TABLE_LIB_SQL = """create table sqllib_sql (
    id integer primary key not null,
    title text not null,
    description text,
    statement text not null,
    category integer
);"""