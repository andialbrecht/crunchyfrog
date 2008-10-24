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

"""Common widgets"""

from gettext import gettext as _
import os

import gnomevfs
import gobject
import gtk
import pango

from kiwi.ui import dialogs

from cf.backends import DBConnectError, DBConnection
from cf.datasources import DatasourceInfo
from cf.ui import GladeWidget


class ConnectionButton(GladeWidget):
    """Connection chooser used in toolbars.

    It is always bound to an SQLEditor.
    """

    def __init__(self, app, xml):
        GladeWidget.__init__(self, app, xml, "tb_connection")
        self._setup_widget()
        self.set_editor(None)
        self.app.datasources.connect("datasource-modified",
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

    def on_new_connection(self, item, datasource_info):
        try:
            conn = datasource_info.dbconnect()
            self._editor.set_connection(conn)
            self.set_editor(self._editor)
        except DBConnectError, err:
            dialogs.error(_(u"Connection failed"), str(err))

    def on_manage_connections(self, *args):
        self.manage_connections()

    def on_set_connection(self, item, connection):
        self._editor.set_connection(connection)
        self.set_editor(self._editor)

    def manage_connections(self):
        """Displays a dialog to manage connections."""
        dlg = ConnectionsDialog(self.app)
        dlg.run()
        dlg.destroy()

    def rebuild_menu(self):
        """Rebuilds the drop-down menu."""
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
                yitem = gtk.MenuItem((_(u"Connection")+" #%s"
                                      % conn.conn_number))
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
        item = gtk.MenuItem(_(u"Show connections"))
        item.connect("activate", lambda *a: self.manage_connections())
        item.show()
        self._menu.append(item)

    def set_editor(self, editor):
        """Associates an editor.

        Arguments:
            editor: SQLEditor instance.
        """
        self._editor = editor
        self.set_sensitive(bool(editor))
        self.rebuild_menu()
        if editor and editor.connection:
            self._label.set_text(editor.connection.get_label())
            markup = ("<b>%s</b>\n%s #%s"
                      % (editor.connection.datasource_info.get_label(),
                         _(u"Connection"), editor.connection.conn_number))
            self.set_tooltip_markup(markup)
        else:
            self._label.set_text("<"+_(u"Not connected")+">")
            self.set_tooltip_markup(_(u"Click to open a connection"))


class DataExportDialog(gtk.FileChooserDialog):
    """Export dialog.

    A modified gtk.FileChooserDialog for exporting data.

    Usage example
    =============

        .. sourcecode:: python

            >>> from cf.ui.widgets import DataExportDialog
            >>> import gtk
            >>> data = [["foo", 1, True], ["bar", 2, False]]
            >>> selected = [2,]
            >>> statement = ("select name, anumber, anotherfield "
                              from foo limit 3;"
            >>> description = (("name", str, None, None, None, None, None),
            ...          ("anumber", int, None, None, None, None, None),
            ...          ("anotherfield", bool, None, None, None, None, None))
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
        self.export_selection = gtk.CheckButton(_(u("_Only export "
                                                    "selected rows")))
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
        if self.open_file.get_active():
            mime = gnomevfs.get_mime_type(opts["uri"])
            app_desc = gnomevfs.mime_get_default_application(mime)
            cmd = app_desc[2].split(" ")
            os.spawnvp(os.P_NOWAIT, cmd[0], cmd+[opts["uri"]])


class ProgressDialog(GladeWidget):
    """Progress dialog with a message

    A simple window with a message, an icon and a progress bar.

    Usage example
    =============

        .. sourcecode:: python

            >>> from cf.ui.widgets import ProgressDialog
            >>> dlg = ProgressDialog(app)
            >>> dlg.show_all()
            >>> dlg = ProgressDialog(app)
            >>> dlg.set_modal(False) # only needed to run it in CF's shell
            >>> dlg.show_all()
            >>> dlg.set_info("This is an information")
            >>> dlg.set_error("Uuups... an error occured")
            >>> dlg.set_progress(0.75)
            >>> dlg.set_finished(True)

    """

    def __init__(self, app, parent=None):
        GladeWidget.__init__(self, app, "crunchyfrog", "progressdialog")
        if parent:
            self.reparent(parent)

    def on_close(self, *args):
        self.destroy()

    def set_progress(self, fraction):
        """Sets fraction for progress bar

        :Parameter:
            fraction
                The fraction (``float``)
        """
        self.xml.get_widget("progress_progress").set_fraction(fraction)

    def set_error(self, message):
        """Displays an error

        :Parameter:
            message
                Error message
        """
        message = gobject.markup_escape_text(message)
        self.xml.get_widget("progress_label").set_markup("<b>"+message+"</b>")
        self.xml.get_widget("progress_image").set_from_stock(
            "gtk-dialog-error", gtk.ICON_SIZE_DIALOG)

    def set_info(self, message):
        """Displays an information

        :Parameter:
            message
                A message
        """
        message = gobject.markup_escape_text(message)
        self.xml.get_widget("progress_label").set_markup("<b>"+message+"</b>")
        self.xml.get_widget("progress_image").set_from_stock(
            "gtk-dialog-info", gtk.ICON_SIZE_DIALOG)

    def set_finished(self, finished):
        """Activates/deactivates close button

        :Parameter:
            finished
                If ``True`` the close button gets sensitive.
        """
        self.xml.get_widget("progress_btn_close").set_sensitive(finished)


class ConnectionsWidget(GladeWidget):
    """Lists datasources and active connections"""

    def __init__(self, app, xml="crunchyfrog"):
        GladeWidget.__init__(self, app, xml, "connections_widget")
        self.refresh()

    def _setup_widget(self):
        self.list_conn = self.xml.get_widget("list_connections")
        model = gtk.TreeStore(gobject.TYPE_PYOBJECT, str)
        model.set_sort_column_id(1, gtk.SORT_ASCENDING)
        self.list_conn.set_model(model)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=1)
        self.list_conn.append_column(col)

    def _setup_connections(self):
        sel = self.list_conn.get_selection()
        sel.connect("changed", self.on_selection_changed)
        self.app.datasources.connect("datasource-added",
                                     self.on_datasource_added)
        self.app.datasources.connect("datasource-deleted",
                                     self.on_datasource_deleted)
        self.app.datasources.connect("datasource-modified",
                                     self.on_datasource_modified)

    def on_connect(self, *args):
        sel = self.list_conn.get_selection()
        model, iter = sel.get_selected()
        if not iter:
            return
        obj = model.get_value(iter, 0)
        if not isinstance(obj, DatasourceInfo):
            return
        conn = obj.dbconnect()
        conn.connect("closed", self.on_connection_closed)
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == conn.datasource_info:
                citer = model.append(iter)
                model.set(citer, 0, conn, 1, conn.get_label())
                break
            iter = model.iter_next(iter)

    def on_disconnect(self, *args):
        sel = self.list_conn.get_selection()
        model, iter = sel.get_selected()
        if not iter:
            return
        obj = model.get_value(iter, 0)
        if not isinstance(obj, DBConnection):
            return
        model.remove(iter)
        obj.close()

    def on_connection_closed(self, connection):
        model = self.list_conn.get_model()
        if not model:
            return
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == connection.datasource_info:
                citer = model.iter_children(iter)
                while citer:
                    if model.get_value(citer, 0) == connection:
                        model.remove(citer)
                        break
                    citer = model.iter_next(citer)
            iter = model.iter_next(iter)

    def on_datasource_added(self, manager, datasource_info):
        model = self.list_conn.get_model()
        iter = model.append(None)
        model.set(iter, 0, datasource_info, 1, datasource_info.get_label())

    def on_datasource_modified(self, manager, datasource_info):
        model = self.list_conn.get_model()
        if not model:
            return
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == datasource_info:
                model.set(iter,
                          0, datasource_info,
                          1, datasource_info.get_label())
                return
            iter = model.iter_next(iter)

    def on_datasource_deleted(self, manager, datasource_info):
        model = self.list_conn.get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == datasource_info:
                model.remove(iter)
                return
            iter = model.iter_next(iter)

    def on_selection_changed(self, selection):
        model, iter = selection.get_selected()
        is_connection = False
        is_ds = False
        if iter:
            obj = model.get_value(iter, 0)
            is_ds = isinstance(obj, DatasourceInfo)
            is_connection = isinstance(obj, DBConnection)
        self.xml.get_widget("btn_disconnect").set_sensitive(is_connection)
        self.xml.get_widget("btn_connect").set_sensitive(is_ds)

    def refresh(self):
        """Initializes the data model"""
        model = self.list_conn.get_model()
        for datasource_info in self.app.datasources.get_all():
            iter = model.append(None)
            model.set(iter, 0, datasource_info, 1, datasource_info.get_label())
            for conn in datasource_info.get_connections():
                citer = model.append(iter)
                model.set(citer, 0, conn, 1, conn.get_label())


class ConnectionsDialog(GladeWidget):
    """Dialog displaying connections"""

    def __init__(self, app):
        GladeWidget.__init__(self, app, "crunchyfrog", "connectionsdialog")

    def _setup_widget(self):
        self.connections = ConnectionsWidget(self.app, self.xml)


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
