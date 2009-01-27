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

"""Object browser"""

import gtk
import gobject

try:
    import sexy
    HAVE_SEXY = True
except ImportError:
    HAVE_SEXY = False

from cf.datasources import DatasourceInfo
from cf.backends import DBConnectError, schema
from cf.ui.editor import SQLView
from cf.ui import pane, dialogs


class DummyNode(object):
    """Placeholder object that is replaced when a node is expanded."""


class Browser(gtk.ScrolledWindow, pane.PaneItem):
    """The object browser (aka navigator) class."""

    __gsignals__ = {
        "object-menu-popup" : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT,
             gobject.TYPE_PYOBJECT)
            ),
    }

    item_id = 'navigator'
    name = _(u'Navigator')
    icon = gtk.STOCK_CONNECT
    detachable = True

    def __init__(self, app, instance):
        """Constructor."""
        self.app = app
        self.instance = instance
        self._setup_widget()
        self._setup_connections()
        self.reset_tree()
        self.guess_hint()

    def _setup_widget(self):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_size_request(250, -1)
        # Model
        self.model = gtk.TreeStore(
            gobject.TYPE_PYOBJECT, # 0 Object
            str,                   # 1 label
            gtk.gdk.Pixbuf,        # 2 icon
            gobject.TYPE_PYOBJECT, # 3 double-click callback
            gobject.TYPE_PYOBJECT, # 4 popup menu callback
            str,                   # 5 tooltip
            )
        self.model.set_sort_column_id(1, gtk.SORT_ASCENDING)
        # TreeView
        self.object_tree = gtk.TreeView(self.model)
        self.add(self.object_tree)
        self.object_tree.set_tooltip_column(5)
        col = gtk.TreeViewColumn()
        renderer = gtk.CellRendererPixbuf()
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, 'pixbuf', 2)
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'text', 1)
        self.object_tree.append_column(col)
        self.object_tree.set_headers_visible(False)
        self.object_tree.enable_model_drag_source(
            gtk.gdk.BUTTON1_MASK,
            (("text/plain", gtk.TARGET_SAME_APP, 80),),
            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY
            )

        def drag_data_get(treeview, context, selection, info, timestamp):
            treeselection = treeview.get_selection()
            model, iter = treeselection.get_selected()
            obj = model.get_value(iter, 0)
            # row_draggable(path) doesn't work somehow...
            if isinstance(obj, schema.Node) \
            and not isinstance(obj, schema.Collection):
                text = model.get_value(iter, 1)
            else:
                text = ""
            selection.set('text/plain', 8, text)
            return

        self.object_tree.connect("drag_data_get", drag_data_get)
        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        # Hint
        style = self.object_tree.get_style()
        if HAVE_SEXY:
            lbl = sexy.UrlLabel(_(u'<b>No active data sources</b>\n\n'
                                  u'<a href="#">Click</a> to open the data '
                                  u'source manager.'))
            lbl.connect("url-activated", self.instance.on_datasource_manager)
        else:
            lbl = gtk.Label(_(u'<b>No active data sources</b>\n'
                              u'Select "Edit" &gt; "Data Source Manager"\n'
                              u'to create one.'))
            lbl.set_use_markup(True)
        lbl.set_alignment(0.5, 0)
        lbl.set_padding(15, 15)
        self._hint = gtk.EventBox()
        self._hint.add(lbl)
        self._hint.modify_bg(gtk.STATE_NORMAL, style.white)

    def _setup_connections(self):
        self.app.datasources.connect('datasource-added',
                                     self.on_datasource_added)
        self.app.datasources.connect('datasource-deleted',
                                     self.on_datasource_deleted)
        self.app.datasources.connect('datasource-modified',
                                     self.on_datasource_modified)
        self.object_tree.connect('button-press-event',
                                 self.on_button_press_event)
        self.object_tree.connect('row-expanded', self.on_row_expanded)
        sel = self.object_tree.get_selection()
        sel.connect('changed', self.on_object_tree_selection_changed)

    def _create_dsinfo_menu(self, model, iter, popup):

        def connect(item, datasource_info):
            try:
                datasource_info.dbconnect()
                self.on_object_tree_selection_changed(self.object_tree.get_selection())
            except DBConnectError, err:
                dialogs.error(_(u"Connection failed"), str(err))

        def disconnect(item, datasource_info):
            datasource_info.dbdisconnect()
            iter = self.get_iter_for_datasource(datasource_info)
            model = self.object_tree.get_model()
            self.object_tree.collapse_row(model.get_path(iter))

        datasource_info = model.get_value(iter, 0)
        if datasource_info.get_connections():
            lbl = _(u"Disconnect")
            cb = disconnect
        else:
            lbl = _(u"Connect")
            cb = connect
        item = gtk.MenuItem(lbl)
        item.connect("activate", cb, datasource_info)
        popup.append(item)
        return popup

    def guess_hint(self):
        if self.object_tree.get_model().get_iter_first():
            if not self.get_child() == self.object_tree:
                self.remove(self._hint.get_parent())
                self.add(self.object_tree)
        else:
            if not self.get_child() == self._hint:
                self.remove(self.object_tree)
                self.add_with_viewport(self._hint)
        self.show_all()

    def _show_popup_menu(self, treeview, event):
        """Build and show the popup menu on RMB."""
        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = treeview.get_path_at_pos(x, y)
        popup = gtk.Menu()
        if pthinfo is None:
            item = gtk.MenuItem(_(u"Add data source"))
            item.connect("activate", self.instance.on_datasource_manager)
            popup.append(item)
        else:
            path, col, cellx, celly = pthinfo
            treeview.grab_focus()
            treeview.set_cursor( path, col, 0)
            model = treeview.get_model()
            iter = model.get_iter(path)
            obj = model.get_value(iter, 0)
            if model.iter_children(iter):
                item = gtk.ImageMenuItem("gtk-refresh")
                item.connect("activate", self.on_refresh_node, model, iter)
                popup.append(item)
            if obj.has_details:
                item = gtk.MenuItem(_(u"Details"))
                item.connect("activate", self.on_show_details, obj, model, iter)
                popup.append(item)
            if popup.get_children():
                popup.append(gtk.SeparatorMenuItem())
            cb = model.get_value(iter, 4)
            if cb:
                try:
                    popup = cb(model, iter, popup)
                except:
                    import traceback; traceback.print_exc()
            self.emit("object-menu-popup", popup, model.get_value(iter, 0))
        if popup.get_children():
            popup.show_all()
            popup.popup( None, None, None, event.button, time)

    def _run_dblclick_action(self, treeview, event):
        """Determine an action for a doubleclick on a node and run it."""
        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = treeview.get_path_at_pos(x, y)
        if pthinfo is not None:
            path, col, cellx, celly = pthinfo
            treeview.grab_focus()
            treeview.set_cursor( path, col, 0)
            model = treeview.get_model()
            iter_ = model.get_iter(path)
            obj = model.get_value(iter_, 0)
            if isinstance(obj, DatasourceInfo) \
            and not obj.internal_connection:
                self.instance.statusbar.push(0, _(u"Connecting..."))
                try:
                    conn = obj.dbconnect()
                    editor = self.instance.editor_create()
                    editor.set_connection(conn)
                    self.on_object_tree_selection_changed(
                        self.object_tree.get_selection())
                except DBConnectError, err:
                    dialogs.error(_(u"Connection failed"), str(err))
                    self.instance.statusbar.pop(0)
            elif isinstance(obj, DatasourceInfo):
                editor = self.instance.editor_create()
                editor.set_connection(obj.internal_connection)

    def on_button_press_event(self, treeview, event):
        if event.type == gtk.gdk._2BUTTON_PRESS \
        and event.button == 1:
            self._run_dblclick_action(treeview, event)
        elif event.button == 3:
            self._show_popup_menu(treeview, event)
            return 1

    def on_datasource_added(self, manager, datasource_info):
        iter_ = self.model.append(None)
        self.set_datasource_info(iter_, datasource_info)
        self.guess_hint()

    def on_datasource_deleted(self, manager, datasource_info):
        iter_ = self.get_iter_for_datasource(datasource_info)
        if not iter_:
            return
        self.model.remove(iter_)
        self.guess_hint()

    def on_datasource_modified(self, manager, datasource_info):
        iter_ = self.get_iter_for_datasource(datasource_info)
        if not iter_:
            return
        self.set_datasource_info(iter_, datasource_info)

    def on_object_tree_selection_changed(self, selection):
        model, iter_ = selection.get_selected()
        if iter_ is None:
            return
        obj = model.get_value(iter_, 0)
        if isinstance(obj, DatasourceInfo):
            if obj.internal_connection:
                server_info = obj.internal_connection.get_server_info()
                if server_info:
                    self.instance.statusbar.push(0, server_info)
                else:
                    self.instance.statusbar.pop(0)
            else:
                self.instance.statusbar.pop(0)
        else:
            comm = model.get_value(iter_, 5) or ""
            self.instance.statusbar.push(0, comm)

    def on_refresh_node(self, menuitem, model, iter):
        citer = model.iter_children(iter)
        while citer:
            model.remove(citer)
            citer = model.iter_children(iter)
        citer = model.append(iter)
        model.set_value(citer, 0, DummyNode())
        self.object_tree.emit("row-expanded", iter, model.get_path(iter))

    def on_row_expanded(self, treeview, iter, path):
        model = treeview.get_model()
        obj = model.get_value(iter, 0)
        citer = model.iter_children(iter)
        if citer:
            cobj = model.get_value(citer, 0)
            if isinstance(cobj, DummyNode):
                datasource_info = self.find_datasource_info(model, citer)
                model.remove(citer)
                if datasource_info.backend.schema and datasource_info.internal_connection:
                    for child in datasource_info.backend.schema.fetch_children(datasource_info.internal_connection, obj) or []:
                        citer = model.append(iter)
                        if child.icon:
                            icon = self.app.load_icon(child.icon,
                                                      gtk.ICON_SIZE_MENU,
                                                      gtk.ICON_LOOKUP_FORCE_SVG)
                        else:
                            icon = None
                        model.set(citer,
                                  0, child,
                                  1, child.name,
                                  2, icon,
                                  5, child.description)
                        if child.has_children:
                            cciter = model.append(citer)
                            model.set(cciter, 0, DummyNode())
                    citer = model.iter_children(iter)
                    if citer:
                        treeview.expand_row(model.get_path(iter), False)

    def on_show_details(self, menuitem, object, model, iter):
        datasource_info = self.find_datasource_info(model, iter)
        if datasource_info.backend.schema:
            data = datasource_info.backend.schema.get_details(
                datasource_info.internal_connection, object)
            if not data:
                return
            nb = gtk.Notebook()
            for key, value in data.items():
                if isinstance(value, basestring):
                    widget = SQLView(self.app)
                    sw = gtk.ScrolledWindow()
                    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                    sw.add(widget)
                    widget.set_editable(False)
                    widget.get_buffer().set_text(value)
                    nb.append_page(sw, gtk.Label(key))
            nb.show_all()

    def find_datasource_info(self, model, iter):
        while iter:
            obj = model.get_value(iter, 0)
            if isinstance(obj, DatasourceInfo):
                return obj
            iter = model.iter_parent(iter)

    def get_iter_for_datasource(self, datasource_info):
        iter_ = self.model.get_iter_first()
        while iter_:
            if self.model.get_value(iter_, 0) == datasource_info:
                return iter_
            iter_ = self.model.iter_next(iter_)
        return None

    def reset_tree(self):
        self.model.clear()
        for datasource_info in self.app.datasources.get_all():
            iter_ = self.model.append(None)
            self.set_datasource_info(iter_, datasource_info)

    def set_datasource_info(self, iter, datasource_info):
        if datasource_info.get_connections():
            ico = self.app.load_icon('stock_connect')
        else:
            ico = self.app.load_icon('stock_disconnect')
        self.model.set(iter,
                  0, datasource_info,
                  1, datasource_info.get_label(),
                  2, ico,
                  3, None,
                  4, self._create_dsinfo_menu,
                  5, datasource_info.description)
        citer = self.model.iter_children(iter)
        if datasource_info.get_connections() \
        and not citer:
            citer = self.model.append(iter)
            self.model.set(citer, 0, DummyNode())
        elif not datasource_info.get_connections() \
        and citer:
            self.model.remove(citer)
