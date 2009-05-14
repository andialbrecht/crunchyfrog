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

"""Common widgets"""

from gettext import gettext as _
import os

import gobject
import gtk
import pango

from cf.db import Connection, Datasource


class ConnectionButton(gtk.MenuToolButton):
    """Connection chooser used in toolbars.

    It is always bound to an SQLEditor.
    """

    def __init__(self, mainwin):
        gtk.MenuToolButton.__init__(self, gtk.STOCK_CONNECT)
        self.app = mainwin.app
        self.mainwin = mainwin
        self._editor = None
        self._setup_widget()
        self.set_editor(None)
        self.app.datasources.connect("datasource-changed",
                                     lambda *a: self.rebuild_menu())
        self.app.datasources.connect("datasource-added",
                                     lambda *a: self.rebuild_menu())
        self.app.datasources.connect("datasource-deleted",
                                     lambda *a: self.rebuild_menu())

    def _setup_widget(self):
        lbl = gtk.Label("Not connected")
        lbl.set_max_width_chars(15)
        lbl.set_ellipsize(pango.ELLIPSIZE_END)
        lbl.set_use_markup(True)
        lbl.show_all()
        self.set_label_widget(lbl)
        self._label = lbl
        self._menu = gtk.Menu()
        self.set_menu(self._menu)

    def rebuild_menu(self):
        """Rebuilds the drop-down menu."""
        rebuild_connection_menu(self._menu, self.mainwin, self._editor)

    def set_editor(self, editor):
        """Associates an editor.

        Arguments:
            editor: SQLEditor instance.
        """
        from cf.ui.editor import Editor  # Import hook
        if self._editor:
            sig = self._editor.get_data('cf::connbtn::sig_conn_changed')
            if sig:
                self._editor.disconnect(sig)
                self._editor.set_data('cf::connbtn::sig_conn_changed', None)
        self._editor = editor
        self.set_sensitive(bool(editor))
        self.rebuild_menu()
        if editor is not None and isinstance(editor, Editor):
            sig = editor.connect('connection-changed',
                                 lambda *a: self.set_editor(editor))
            editor.set_data('cf::connbtn::sig_conn_changed', sig)
        if editor and editor.connection:
            self._label.set_text(editor.connection.get_label())
            markup = ("<b>%s</b>\n%s #%s"
                      % (editor.connection.datasource.get_label(),
                         _(u"Connection"), editor.connection.num))
            self.set_tooltip_markup(markup)
        else:
            self._label.set_text("<"+_(u"Not connected")+">")
            self.set_tooltip_markup(_(u"Click to open a connection"))


def rebuild_connection_menu(menu, win, editor=None):
    """Rebuilds the connection chooser menu.

    Arguments:
      menu: The menu to rebuild.
      win: A main window instance.
      editor: The editor for which the menu is build (default: None).
    """
    while menu.get_children():
        menu.remove(menu.get_children()[0])
    if editor is None:
        return

    def create_and_assign(menuitem, datasource, editor):
        conn = datasource.dbconnect()
        if conn is not None:
            editor.set_connection(conn)

    add_sep = False
    for conn in win.app.datasources.get_connections():
        add_sep = True
        item = gtk.MenuItem(conn.get_label())
        item.connect('activate', lambda m, c, e: e.set_connection(c),
                     conn, editor)
        item.show()
        menu.append(item)

    if add_sep:
        item = gtk.SeparatorMenuItem()
        item.show()
        menu.append(item)

    item = gtk.MenuItem(_(u'_New connection'))
    item.show()
    menu.append(item)

    dsmenu = gtk.Menu()
    dsinfos = win.app.datasources.get_all()
    dsinfos.sort(lambda x, y: cmp(x.get_label().lower(),
                                  y.get_label().lower()))
    for dsinfo in dsinfos:
        dsitem = gtk.MenuItem(dsinfo.get_label())
        dsitem.show()
        dsitem.connect('activate', create_and_assign, dsinfo, editor)
        dsmenu.append(dsitem)
    item.set_submenu(dsmenu)

    action = win._get_action('query-show-connections')
    item = action.create_menu_item()
    item.show()
    menu.append(item)
    action = win._get_action('query-connection-disconnect')
    item = action.create_menu_item()
    action.set_sensitive(editor.connection is not None)
    item.show()
    menu.append(item)


class DataExportDialog(gtk.FileChooserDialog):
    """Modified gtk.FileChooserDialog for exporting data.

    Usage example:

      >>> from cf.ui.widgets import DataExportDialog
      >>> import gtk
      >>> data = [['foo', 1, True], ['bar', 2, False]]
      >>> selected = [2,]
      >>> statement = ('select name, anumber, anotherfield '
          from foo limit 3;'
      >>> description = (('name', str, None, None, None, None, None),
      ...          ('anumber', int, None, None, None, None, None),
      ...          ('anotherfield', bool, None, None, None, None, None))
      >>> dlg = DataExportDialog(app, instance.widget,
      ...                        data, selected, statement, description)
      >>> if dlg.run() == gtk.RESPONSE_OK:
      ...     dlg.hide()
      ...     dlg.export_data()
      ...
      >>> dlg.destroy()
    """

    def __init__(self, app, parent, data, selected, statement, description):
        """
        The constructor of this class takes 6 arguments:

        :Parameter:
            app
                `CFApplication`_ instance
            parent
                The parent widget, usualy something like
                ``self.instance.widget``
            data
                List of rows (``[ [col1, col2, col3], ...]``)
            selected
                List of indices of selected rows (``None`` means that no
                rows are selected)
            statement
                The SQL statement that produced the data.
                This parameter is only used by some filters to give additional
                information.
            description
                A DB-API2-like description.
                Read the comments on the ``description`` attribute of cursor
                objects in `PEP 249`_ for details.


        .. Note:: Usually there's no need to define ``data`` and
          ``description``
            by hand. If it's a DB-API2-based backend, these parameters are
            retrieved from the cursor object (``cursor.fetchall()`` and
            ``cursor.description``).

        .. _CFApplication: cf.app.CFApplication.html
        .. _PEP 249: http://www.python.org/dev/peps/pep-0249/
        """
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
        cfg = self.app.config
        vbox = gtk.VBox()
        vbox.set_spacing(5)
        self.set_extra_widget(vbox)
        self.edit_export_options = gtk.CheckButton(_(u"_Edit export options"))
        vbox.pack_start(self.edit_export_options, False, False)
        self.export_selection = gtk.CheckButton(_((u"_Only export "
                                                   u"selected rows")))
        self.export_selection.set_sensitive(bool(self.selected))
        vbox.pack_start(self.export_selection, False, False)
        self.open_file = gtk.CheckButton(_(u"_Open file when finished"))
        vbox.pack_start(self.open_file, False, False)
        vbox.show_all()
        if cfg.get("editor.export.recent_folder"):
            self.set_current_folder(cfg.get("editor.export.recent_folder"))
        self._setup_filter()

    def _setup_filter(self):
        cfg = self.app.config
        recent_filter = None
        from cf.plugins.core import PLUGIN_TYPE_EXPORT
        for plugin in self.app.plugins.get_plugins(PLUGIN_TYPE_EXPORT, True):
            filter = gtk.FileFilter()
            filter.set_name(plugin.file_filter_name)
            for pattern in plugin.file_filter_pattern:
                filter.add_pattern(pattern)
            for mime in plugin.file_filter_mime:
                filter.add_mime_type(mime)
            self.add_filter(filter)
            filter.set_data("plugin", plugin)
            if cfg.get("editor.export.recent_filter", None) == plugin.id:
                recent_filter = filter
        if recent_filter:
            self._filter_changed(recent_filter)
        else:
            self._filter_changed(self.get_filter())

    def _setup_connections(self):
        self.connect("notify::filter", self.on_filter_changed)

    def on_filter_changed(self, dialog, param):
        gobject.idle_add(self._filter_changed, self.get_filter())

    def _filter_changed(self, filter):
        plugin = filter.get_data("plugin")
        self.edit_export_options.set_sensitive(plugin.has_options)

    def export_data(self):
        """Exports the data

        This method handles the export options given in the dialog and
        calls the ``export`` method of the choosen `export filter`_.

        .. _export filter: cf.plugins.core.ExportPlugin.html
        """
        self.app.config.set("editor.export.recent_folder",
                            self.get_current_folder())
        plugin = self.get_filter().get_data("plugin")
        self.app.config.set("editor.export.recent_filter", plugin.id)
        if self.export_selection.get_property("sensitive") \
        and self.export_selection.get_active():
            rows = []
            for i in self.selected:
                rows.append(self.data[i])
        else:
            rows = self.data
        opts = {"filename": self.get_filename(),
                "uri": self.get_uri(),
                "query": self.statement}
        if self.edit_export_options.get_property("sensitive") \
        and self.edit_export_options.get_active():
            opts.update(plugin.show_options(self.description, rows))
        plugin.export(self.description, rows, opts)
        if self.open_file is not None and self.open_file.get_active():
            gtk.show_uri(gtk.gdk.screen_get_default(), opts['uri'], 0)


class ConnectionsDialog(object):
    """Lists datasources and active connections"""

    def __init__(self, win, xml="connectionsdialog"):
        self.app = win.app
        self.instance = win
        self.builder = gtk.Builder()
        self.builder.set_translation_domain('crunchyfrog')
        self.builder.add_from_file(self.app.get_glade_file('%s.glade' % xml))
        self.builder.connect_signals(self)
        self.dlg = self.builder.get_object('connectionsdialog')
        self._setup_widget()
        self._setup_connections()
        self.refresh()

    def _setup_widget(self):
        self.list_conn = self.builder.get_object("list_connections")
        model = gtk.ListStore(gobject.TYPE_PYOBJECT,  # 0 object
                              str,                    # 1 label
                              bool,                   # 2 is separator
                              int,                    # 3 font weight
                              str,                    # 4 stock-id
                              str,                    # 5 sort name
                              )
        model.set_sort_column_id(5, gtk.SORT_ASCENDING)
        self.list_conn.set_model(model)
        col = gtk.TreeViewColumn()
        renderer = gtk.CellRendererPixbuf()
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, 'stock-id', 4)
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'text', 1)
        col.add_attribute(renderer, 'weight', 3)
        self.list_conn.append_column(col)
        self.list_conn.set_hover_expand(True)
        self.list_conn.set_row_separator_func(lambda m, i: m.get_value(i, 2))

    def _setup_connections(self):
        sel = self.list_conn.get_selection()
        sel.connect("changed", self.on_selection_changed)
        self.app.datasources.connect("datasource-added",
                                     self.on_datasource_added)
        self.app.datasources.connect("datasource-deleted",
                                     self.on_datasource_deleted)
        self.app.datasources.connect("datasource-changed",
                                     self.on_datasource_modified)

    # ---------
    # Callbacks
    # ---------

    def on_assign_to_editor(self, *args):
        sel = self.list_conn.get_selection()
        model, iter = sel.get_selected()
        if not iter:
            return
        obj = model.get_value(iter, 0)
        editor = self.instance.get_active_editor()
        if editor is None:
            return
        editor.set_connection(obj)

    def on_connect(self, *args):
        sel = self.list_conn.get_selection()
        model, iter = sel.get_selected()
        if not iter:
            return
        obj = model.get_value(iter, 0)
        if not isinstance(obj, Datasource):
            return
        conn = obj.dbconnect()
        conn.connect("closed", self.on_connection_closed)
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == conn.datasource:
                citer = model.insert_after(iter)
                model.set(citer, 0, conn, 1, conn.get_label(short=True),
                          5, conn.get_label())
                break
            iter = model.iter_next(iter)
        self.list_conn.expand_to_path(model.get_path(citer))
        sel.select_iter(citer)

    def on_disconnect(self, *args):
        sel = self.list_conn.get_selection()
        model, iter = sel.get_selected()
        if not iter:
            return
        obj = model.get_value(iter, 0)
        if not isinstance(obj, Connection):
            return
        model.remove(iter)
        obj.close()

    def on_connection_closed(self, connection):
        model = self.list_conn.get_model()
        if not model:
            return
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == connection.datasource:
                citer = model.iter_children(iter)
                while citer:
                    if model.get_value(citer, 0) == connection:
                        model.remove(citer)
                        break
                    citer = model.iter_next(citer)
            iter = model.iter_next(iter)

    def on_datasource_added(self, manager, datasource):
        model = self.list_conn.get_model()
        iter = model.append(None)
        model.set(iter, 0, datasource, 1, datasource.get_label())

    def on_datasource_modified(self, manager, datasource):
        model = self.list_conn.get_model()
        if not model:
            return
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == datasource:
                model.set(iter,
                          0, datasource,
                          1, datasource.get_label())
                return
            iter = model.iter_next(iter)

    def on_datasource_deleted(self, manager, datasource):
        model = self.list_conn.get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == datasource:
                model.remove(iter)
                return
            iter = model.iter_next(iter)

    def on_selection_changed(self, selection):
        model, iter = selection.get_selected()
        is_connection = False
        is_ds = False
        if iter:
            obj = model.get_value(iter, 0)
            is_ds = isinstance(obj, Datasource)
            is_connection = isinstance(obj, Connection)
        self.builder.get_object('btn_disconnect').set_sensitive(is_connection)
        self.builder.get_object('btn_connect').set_sensitive(is_ds)
        btn_assign = self.builder.get_object('btn_assign')
        editor = self.instance.get_active_editor()
        btn_assign.set_sensitive(bool(is_connection and editor))

    # --------------
    # Public methods
    # --------------

    def run(self):
        """Run the dialog."""
        return self.dlg.run()

    def destroy(self):
        """Destroy the dialog."""
        self.dlg.destroy()

    def refresh(self):
        """Refresh the data model"""
        model = self.list_conn.get_model()
        for datasource in self.app.datasources.get_all():
            iter = model.append(None)
            model.set(iter, 0, datasource,
                      1, datasource.get_label(),
                      2, False,
                      3, pango.WEIGHT_BOLD,
                      5, datasource.get_label())
            citer = None
            for conn in datasource.get_connections():
                citer = model.append(None)
                model.set(citer,
                          0, conn,
                          1, conn.get_label(short=True),
                          2, False,
                          5, conn.get_label())
            if citer is None:
                model.set_value(iter, 4, gtk.STOCK_DISCONNECT)
            else:
                model.set_value(iter, 4, gtk.STOCK_CONNECT)
        self.list_conn.expand_all()


class CustomImageMenuItem(gtk.ImageMenuItem):
    """Menu item with custom image.

    This widget simplifies the creation of an gtk.ImageMenuItem with an
    custom image. icon_name is used to lookup an icon in the default GTK
    icon theme and so it is not restricted to stock id's. The additional method
    set_markup() can be used to set a markup string as the menu items
    label.

    Note: It is not recommended to use set_markup() because it is very
      unusual to have formatted text in menu items.
    """

    def __init__(self, icon_name, label, is_markup=False):
        """
        The constructor of this class takes up to 3 arguments:

        :Parameter:
            icon_name
                Name of the icon or stock id
            label
                Menu item label
            is_markup
                If ``True``, ``label`` is set as markup (default: ``False``)
        """
        gtk.ImageMenuItem.__init__(self, "gtk-open")
        self.set_icon_name(icon_name)
        if is_markup:
            self.set_markup(label)
        else:
            self.set_label(label)

    def set_icon_name(self, icon_name):
        """Sets the image

        Args:
          icon_name: Icon name of the image.
        Raises:
          GError: if the icon isn't present in icon theme.
        """
        it = gtk.icon_theme_get_default()
        pb = it.load_icon(icon_name, gtk.ICON_SIZE_MENU,
                          gtk.ICON_LOOKUP_FORCE_SVG)
        img = gtk.image_new_from_pixbuf(pb)
        self.set_image(gtk.image_new_from_pixbuf(pb))

    def set_label(self, label):
        """Sets the label

        :Parameter:
            label
                Menu item label
        """
        self.get_children()[0].set_label(label)

    def set_markup(self, markup):
        """Sets the label as markup

        :Parameter:
            markup
                Menu item markup
        """
        self.get_children()[0].set_markup(markup)
