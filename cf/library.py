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
    - Re-order categories and statements
    - Double-click / open in editor (drag'n'drop)
"""

import gtk
import gobject
import pango

from cf import utils
from cf.plugins.core import BottomPanePlugin
from cf.plugins.mixins import InstanceMixin, UserDBMixin
from cf.ui.pane import PaneItem


class Category(object):
    """Data object holding a category."""

    def __init__(self, id_, name, parent=None):
        self.id = id_
        self.name = name
        self.parent = parent

    def get_update_statement(self):
        """Returns an update SQL."""
        sql = ("update sqllib_cat set name = ?, parent = ? where id = ?")
        return sql, (self.name, self.parent, self.id)

    def get_insert_statement(self):
        """Returns an insert SQL."""
        sql = "insert into sqllib_cat (name, parent) values (?, ?)"
        return sql, (self.name, self.parent )

    def get_delete_statement(self):
        """Returns a delete SQL."""
        sql = 'delete from sqllib_cat where id = ?'
        return sql, (self.id,)


class Statement(object):
    """Data object holding a statement."""

    def __init__(self, id_, title, statement, description=None, category=None):
        self.id = id_
        if title is None:
            title = utils.normalize_sql(statement)
        self.title = title
        self.statement = statement
        self.description = description
        self.category = category

    def get_update_statement(self):
        """Returns an update SQL."""
        sql = ("update sqllib_sql set title = ?, statement = ?, "
               "description = ?, category = ? where id = ?")
        return sql, (self.title or self.statement, self.statement,
                     self.description or None, self.category or None,
                     self.id)

    def get_insert_statement(self):
        """Returns an insert SQL."""
        sql = ("insert into sqllib_sql (title, statement, description, "
               "category) values (?, ?, ?, ?)")
        return sql, (self.title or self.statement, self.statement,
                     self.description or None, self.category or None)

    def get_delete_statement(self):
        """Returns a delete SQL."""
        sql = 'delete from sqllib_sql where id = ?'
        return sql, (self.id,)


class SQLLibraryPlugin(BottomPanePlugin, InstanceMixin, UserDBMixin):
    """SQL library plugin"""

    id = "crunchyfrog.plugin.library"
    name = _(u"Library")
    description = _(u"A personal SQL library")
    icon = "stock_book_green"
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://cf.andialbrecht.de"
    version = "0.1"

    def __init__(self, app):
        BottomPanePlugin.__init__(self, app)
        self._views = {}

    def on_save_to_library(self, instance):
        editor = instance.get_active_editor()
        if editor is None:
            return
        statement = editor.get_text()
        entry = Statement(None, None, statement)
        self.save_entry(entry)

    def init_instance(self, instance):
        """Initialize instance."""
        view = SQLLibraryView(self.app, instance, self)
        view.refresh()
        instance.side_pane.add_item(view)
        group = None
        for group in instance.ui.get_action_groups():
            if group.get_name() == 'editor':
                break
        assert group is not None
        entries = (
            ('lib-save', None,
             _(u'Save to library'), None,
             _(u'Save content of the current editor to SQL library.'),
             lambda menuitem: self.on_save_to_library(instance)),
        )
        group.add_actions(entries)
        merge_id = instance.ui.add_ui_from_string(UI)
        self._views[instance] = (view, merge_id)

    def deactivate_instance(self, instance):
        """De-activates an view."""
        if instance in self._views:
            view, merge_id = self._views.pop(instance)
            instance.ui.remove_ui(merge_id)
            for group in instance.ui.get_action_groups():
                if group.get_name() == 'editor':
                    action = group.get_action('lib-save')
                    if action is not None:
                        group.remove_action(action)
                        break
            view.destroy()

    def shutdown(self):
        """Shutdown plugin."""
        while self._views:
            self.deactivate_instance(self._views.keys()[0])

    def userdb_init(self):
        """Initialize user db."""
        if self.userdb.get_table_version("sqllib_cat") == None:
            self.userdb.create_table("sqllib_cat", "0.1", TABLE_LIB_CAT)
        if self.userdb.get_table_version("sqllib_sql") == None:
            self.userdb.create_table("sqllib_sql", "0.1", TABLE_LIB_SQL)

    def get_entries(self, parent=None):
        """Return rows from userdb that belong to parent (an ID).

        This yields a tuple (is_category, id, title, description, statement).
        """
        ret = []
        sql = 'select id, name, parent from sqllib_cat'
        if parent is not None:
            sql += ' where parent = %d' % parent
        else:
            sql += ' where parent is null'
        [ret.append(Category(row[0], row[1], row[2]))
         for row in self.userdb.cursor.execute(sql)]
        sql = ('select id, title, statement, description, category '
               'from sqllib_sql')
        if parent is not None:
            sql += ' where category = %d' % parent
        else:
            sql += ' where category is null'
        [ret.append(Statement(row[0], row[1], row[2], row[3], row[4]))
         for row in self.userdb.cursor.execute(sql)]
        return ret

    def save_entry(self, entry):
        """Save entry back to library."""
        if entry.id is None:
            sql, params = entry.get_insert_statement()
        else:
            sql, params = entry.get_update_statement()
        self.userdb.cursor.execute(sql, params)
        self.userdb.conn.commit()
        if entry.id is None:
            entry.id = self.userdb.cursor.lastrowid
        for instance, (view, merge_id) in self._views.iteritems():
            view.refresh()
        return entry.id

    def delete_entry(self, entry):
        """Deletes entry in library."""
        sql, params = entry.get_delete_statement()
        self.userdb.cursor.execute(sql, params)
        self.userdb.conn.commit()
        for instance, (view, merge_id) in self._views.iteritems():
            view.remove_entry(entry)


class SQLLibraryView(gtk.ScrolledWindow, PaneItem):

    name = _(u'Library')
    icon = 'stock_book_green'
    detachable = True

    def __init__(self, app, instance, library):
        """Constructor."""
        self.app = app
        self.instance = instance
        self.lib = library
        gtk.ScrolledWindow.__init__(self)
        PaneItem.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.model = gtk.TreeStore(gobject.TYPE_PYOBJECT,   # 0 item
                                   str,                     # 1 stock id
                                   str,                     # 2 label
                                   str,                     # 3 content
                                   bool,                    # 4 editable
                                   )
        self.list = gtk.TreeView(self.model)
        col = gtk.TreeViewColumn()
        renderer = gtk.CellRendererPixbuf()
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, 'stock-id', 1)
        renderer = gtk.CellRendererText()
        renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'text', 2)
        col.add_attribute(renderer, 'editable', 4)
        renderer.connect('edited', self.on_entry_edited)
        self.list.append_column(col)
        self.list.set_headers_visible(False)
        self.add(self.list)
        self.list.show()
        self.list.connect("button-press-event", self.on_button_press_event)
        # Drag'n'drop
        targets = [
            ('MY_TREE_MODEL_ROW', gtk.TARGET_SAME_WIDGET, 0),
            ('text/plain', 0, 1),
        ]
        self.list.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, targets,
                                           gtk.gdk.ACTION_DEFAULT|
                                           gtk.gdk.ACTION_MOVE)
        self.list.enable_model_drag_dest(targets, gtk.gdk.ACTION_DEFAULT)
        self.list.connect('drag_data_get', self.on_drag_data_get)
        self.list.connect('drag_data_received', self.on_drag_data_received)

    def _get_entry(self, is_cat, id_, iter_=None):
        """Returns path for an entry."""
        if iter_ is None:
            iter_ = self.model.get_iter_root()
        while iter_:
            obj = self.model.get_value(iter_, 0)
            if isinstance(obj, Category) and is_cat and obj.id == id_:
                return iter_
            elif isinstance(obj, Statement) and obj.id == id_:
                return iter_
            if self.model.iter_has_child(iter_):
                citer_ = self.model.iter_children(iter_)
                result = self._get_entry(is_cat, id_, citer_)
                if result is not None:
                    return result
            iter_ = self.model.iter_next(iter_)
        return None

    def _run_dblclick_action(self, treeview, event):
        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = treeview.get_path_at_pos(x, y)
        if pthinfo is None:
            return
        model = treeview.get_model()
        obj = model.get_value(model.get_iter(pthinfo[0]), 0)
        if isinstance(obj, Category):
            if not treeview.row_expanded(pthinfo[0]):
                treeview.expand_row(pthinfo[0], False)
        else:
            editor = self.instance.editor_create()
            editor.set_text(obj.statement)

    def _show_popup_menu(self, treeview, event):
        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = treeview.get_path_at_pos(x, y)
        if pthinfo is not None:
            model = treeview.get_model()
            obj = model.get_value(model.get_iter(pthinfo[0]), 0)
        else:
            obj = None
        menu = gtk.Menu()
        if obj is not None:
            if isinstance(obj, Category):
                item = gtk.MenuItem(_(u'Add category'))
                item.connect('activate', self.on_add_category, obj)
                item.show()
                menu.append(item)
            item = gtk.MenuItem(_(u'Rename'))
            item.connect('activate', self.on_entry_rename,
                         treeview, pthinfo[0])
            menu.append(item)
            item = gtk.MenuItem(_(u'Delete'))
            item.connect('activate', self.on_entry_delete, obj)
            item.show()
            menu.append(item)
        else:
            item = gtk.MenuItem(_(u'Add category'))
            item.connect('activate', self.on_add_category)
            item.show()
            menu.append(item)
        menu.show_all()
        menu.popup( None, None, None, event.button, time)

    # ---
    # Callbacks
    # ---

    def on_add_category(self, menuitem, parent=None):
        model = self.list.get_model()
        if parent is not None:
            iter_ = self._get_entry(True, parent.id)
        else:
            iter_ = model.append(None)
        obj = Category(None, _(u'Unknown'))
        model.set(iter_, 0, obj, 1, gtk.STOCK_OPEN,
                  2, obj.name, 3, None, 4, True)
        self.list.set_cursor(model.get_path(iter_), self.list.get_column(0),
                             True)

    def on_button_press_event(self, treeview, event):
        if event.type == gtk.gdk._2BUTTON_PRESS \
        and event.button == 1:
            self._run_dblclick_action(treeview, event)
        elif event.button == 3:
            self._show_popup_menu(treeview, event)
            return 1

    def on_drag_data_get(self, treeview, context, selection, target_id, etime):
        treeselection = treeview.get_selection()
        model, iter_ = treeselection.get_selected()
        obj = model.get_value(iter_, 0)
        if target_id == 0:  # drag'n'drop in treeview
            data = '%s::%s' % ((isinstance(obj, Category) and '1' or ''),
                               obj.id)
        elif isinstance(obj, Statement):
            data = obj.statement or obj.title
        else:
            data = ''
        selection.set(selection.target, 8, data)

    def on_drag_data_received(self, treeview, context, x, y, selection,
                              target_id, etime):
        model = treeview.get_model()
        data = selection.data
        drop_info = treeview.get_dest_row_at_pos(x, y)
        tbd = []
        if drop_info is not None:
            path, position = drop_info
            if position in [gtk.TREE_VIEW_DROP_BEFORE,
                            gtk.TREE_VIEW_DROP_AFTER]:
                return
            iter_ = model.get_iter(path)
            obj = model.get_value(iter_, 0)
            if target_id == 1:
                if (isinstance(obj, Statement)
                    and (position == gtk.TREE_VIEW_DROP_INTO_OR_AFTER
                         or position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE)):
                    obj.statement = data
                    tbd.append(obj)
                elif (position == gtk.TREE_VIEW_DROP_INTO_OR_AFTER
                      or position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                    tbd.append(
                        Statement(None, data, data, category=obj.id))
            else:
                x1, x2 = data.split('::', 1)
                oiter = self._get_entry(bool(x1), int(x2))
                other_obj = model.get_value(oiter, 0)
                if (isinstance(obj, Category)
                    and (position == gtk.TREE_VIEW_DROP_INTO_OR_AFTER
                         or position == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE)):
                    if isinstance(other_obj, Statement):
                        other_obj.category = obj.id
                    else:
                        other_obj.parent = obj.id
                    tbd.append(other_obj)
        elif target_id == 1:  # drop from editor
            stmt = Statement(None, data, data)
            tbd.append(stmt)
        if context.action == gtk.gdk.ACTION_MOVE:
            context.finish(True, True, etime)
        for item in tbd:
            self.lib.save_entry(item)
        return

    def on_entry_delete(self, menuitem, entry):
        self.lib.delete_entry(entry)

    def on_entry_edited(self, renderer, path, new_text):
        model = self.list.get_model()
        model.set_value(model.get_iter(path), 2, new_text)
        entry = model.get_value(model.get_iter(path), 0)
        if isinstance(entry, Category):
            entry.name = new_text
        else:
            entry.title = new_text
        entry.id = self.lib.save_entry(entry)

    def on_entry_rename(self, menuitem, treeview, path):
        treeview.set_cursor(path, treeview.get_column(0), True)

    # ---
    # Public methods
    # ---

    def get_selected_item(self):
        """Returns selected item or None."""
        sel = self.list.get_selection()
        model, iter_ = sel.get_selected()
        if iter_ is not None:
            return model.get_value(iter_, 0)
        return None

    def refresh(self, parent=None):
        """Update all entries in the TreeView."""
        for item in self.lib.get_entries(parent):
            is_cat = isinstance(item, Category)
            iter_ = self._get_entry(is_cat, item.id)
            if iter_ is None:
                if isinstance(item, Category):
                    parent = item.parent
                else:
                    parent = item.category
                if parent:
                    iter_ = self.model.append(self._get_entry(True, parent))
                else:
                    iter_ = self.model.append(None)
            if isinstance(item, Category):
                lbl = item.name
                content = None
                ico = gtk.STOCK_OPEN
            else:
                lbl = item.title or item.statement.split('\n')[0]
                content = item.statement
                ico = gtk.STOCK_FILE
            self.model.set_value(iter_, 0, item)
            self.model.set_value(iter_, 1, ico)
            self.model.set_value(iter_, 2, lbl)
            self.model.set_value(iter_, 3, content)
            self.model.set_value(iter_, 4, True)
            if is_cat:
                self.refresh(item.id)

    def remove_entry(self, entry):
        """Removes an entry form the list."""
        iter_ = self._get_entry(isinstance(entry, Category), entry.id)
        self.list.get_model().remove(iter_)


UI = '''
<menubar name="MenuBar">
  <menu name="Query" action="query-menu-action">
    <placeholder name="query-extensions">
      <separator />
      <menuitem name="LibSave" action="lib-save" />
    </placeholder>
  </menu>
</menubar>
'''


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
