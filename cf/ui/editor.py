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

"""SQL editor and results view"""

from gettext import gettext as _
import logging
import os
import re
import string
import thread
import time
import urlparse

import gobject
import gtk
import gtksourceview2
import pango

from cf import sqlparse
from cf.backends import Query
from cf.ui import GladeWidget, dialogs
from cf.ui.confirmsave import ConfirmSaveDialog
from cf.ui.pane import PaneItem
from cf.ui.toolbar import CFToolbar
from cf.ui.widgets import DataExportDialog
from cf.ui.widgets.grid import Grid
from cf.ui.widgets.sqlview import SQLView


def to_uri(filename):
    """Converts a filename to URI. It's ok to pass in a URI here."""
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(filename)
    if not scheme:
        uri = urlparse.urlunparse(('file', netloc, path, params,
                                   query, fragment))
    else:
        uri = filename
    return uri


class Editor(GladeWidget, PaneItem):

    name = _(u'Editor')
    icon = gtk.STOCK_EDIT
    detachable = True

    __gsignals__ = {
        "connection-changed" : (gobject.SIGNAL_RUN_LAST,
                                gobject.TYPE_NONE,
                                (gobject.TYPE_PYOBJECT,))
    }

    __gproperties__ = {
        'buffer-dirty': (gobject.TYPE_BOOLEAN,
                         'dirty flag',
                         'is the buffer dirty?',
                         False,
                         gobject.PARAM_READWRITE),
        }

    def __init__(self, win):
        self.app = win.app
        self.instance = win
        self.connection = None
        self._buffer_dirty = False
        self.__conn_close_tag = None
        self._query_timer = None
        self._filename = None
        self._filecontent_read = ""
        GladeWidget.__init__(self, self.instance, "editor", "box_editor")
        self.set_data("win", None)
        self.show_all()

    def do_get_property(self, param):
        if param.name == 'buffer-dirty':
            return self._buffer_dirty

    def do_set_property(self, param, value):
        if param.name == 'buffer-dirty':
            self._buffer_dirty = value

    # Widget setup

    def _setup_widget(self):
        self._setup_textview()
        self._setup_resultsgrid()

    def _setup_textview(self):
        self.textview = SQLView(self.win, self)
        sw = self.xml.get_widget("sw_editor_textview")
        sw.add(self.textview)
        self.textview.buffer.connect('changed', self.on_buffer_changed)

    def _setup_resultsgrid(self):
        self.results = ResultsView(self.instance, self.xml)

    def _setup_connections(self):
        self.textview.connect("populate-popup", self.on_populate_popup)

    # Callbacks

    def on_buffer_changed(self, buffer):
        self.props.buffer_dirty = self.contents_changed()

    def on_close(self, *args):
        self.close()

    def on_connection_closed(self, connection):
        if connection == self.connection and self.__conn_close_tag:
            connection.disconnect(self.__conn_close_tag)
        self.set_connection(None)

    def on_explain(self, *args):
        self.explain()

    def on_populate_popup(self, textview, popup):
        cfg = self.app.config
        sep = gtk.SeparatorMenuItem()
        sep.show()
        popup.append(sep)
        if self.connection and self.connection.provider.reference:
            refviewer = self.instance.get_data("refviewer")
            buffer = self.textview.get_buffer()
            bounds = buffer.get_selection_bounds()
            if bounds:
                url = self.connection.provider.reference.get_context_help_url(buffer.get_text(*bounds))
            else:
                url = None
            if url and refviewer:
                item = gtk.ImageMenuItem("gtk-help")
                item.connect("activate", self.on_show_context_help,
                             refviewer, url)
                item.show()
                popup.append(item)
        item = gtk.CheckMenuItem(_(u"Split statements"))
        item.set_active(cfg.get("sqlparse.enabled"))
        item.connect("toggled", lambda x: cfg.set("sqlparse.enabled",
                                                  x.get_active()))
        item.show()
        popup.append(item)
        item = gtk.ImageMenuItem("gtk-close")
        item.show()
        item.connect("activate", self.on_close)
        popup.append(item)

    def on_query_started(self, query):
        start = time.time()
        # Note: The higher the time out value, the longer the query takes.
        #    50 is a reasonable value anyway.
        #    The start time is for the UI only. The real execution time
        #    is calculated in the Query class.
        self.instance.statusbar.pop(1)
        if self._query_timer is not None:
            gobject.source_remove(self._query_timer)
        self.results.add_separator()
        self.results.add_message(query.statement, type_='query')
        query.path_status = self.results.add_message("")
        self._query_timer = gobject.timeout_add(50, self.update_exectime,
                                                start, query)

    def on_query_finished(self, query, tag_notice):
        if self._query_timer:
            gobject.source_remove(self._query_timer)
            self._query_timer = None
        self.results.set_query(query)
        if query.failed:
            msg = _(u'Query failed (%(sec).3f seconds)')
            msg = msg % {"sec": query.execution_time}
            type_ = 'error'
        elif query.description:
            msg = (_(u"Query finished (%(sec).3f seconds, %(num)d rows)")
                   % {"sec": query.execution_time,
                      "num": query.rowcount})
            type_ = 'info'
        else:
            msg = _(u"Query finished (%(sec).3f seconds, "
                    u"%(num)d affected rows)")
            msg = msg % {"sec": query.execution_time,
                         "num": query.rowcount}
            type_ = 'info'
        self.results.add_message(msg, type_, query.path_status)
        self.instance.statusbar.push(1, msg)
        if self.connection.handler_is_connected(tag_notice):
            self.connection.disconnect(tag_notice)
        self.textview.grab_focus()

    def on_show_context_help(self, menuitem, refviewer, url):
        refviewer.load_url(url)

    def on_show_in_main_window(self, *args):
        gobject.idle_add(self.show_in_main_window)

    def on_show_in_separate_window(self, *args):
        gobject.idle_add(self.show_in_separate_window)

    # Public methods

    def close(self):
        """Close editor, displays a confirmation dialog for unsaved files."""
        if self.contents_changed():
            dlg = ConfirmSaveDialog(self.instance, [self])
            resp = dlg.run()
            if resp == 1:
                ret = dlg.save_files()
            elif resp == 2:
                ret = True
            else:
                ret = False
            dlg.destroy()
        else:
            ret = True
        if ret:
            if self.get_data("win"):
                self.get_data("win").destroy()
            else:
                self.destroy()
            self.instance.set_editor_active(self, False)
            self.instance._editors.remove(self)
            return True

    def commit(self):
        """Commit current transaction, if any."""
        if not self.connection: return
        cur = self.connection.cursor()
        cur.execute("commit")
        cur.close()
        self.results.add_message('COMMIT', 'info')

    def rollback(self):
        """Commit current transaction, if any."""
        if not self.connection: return
        cur = self.connection.cursor()
        cur.execute("rollback")
        cur.close()
        self.results.add_message('ROLLBACK', 'info')

    def begin_transaction(self):
        """Begin transaction."""
        if not self.connection: return
        cur = self.connection.cursor()
        cur.execute("begin")
        cur.close()
        self.results.add_message('BEGIN TRANSACTION', 'info')

    def execute_query(self):
        def exec_threaded(statement):
            cur = self.connection.cursor()
            if self.app.config.get("sqlparse.enabled", True):
                if self.connection:
                    dialect = self.connection.sqlparse_dialect
                else:
                    dialect = None
                stmts = sqlparse.parse(statement, dialect=dialect)
            else:
                stmts = [statement]
            stmts = [unicode(s) for s in stmts]
            for stmt in stmts:
                if not stmt.strip():
                    continue
                query = Query(stmt, cur)
                query.coding_hint = self.connection.coding_hint
                gtk.gdk.threads_enter()
                query.connect("started", self.on_query_started)
                query.connect("finished",
                              self.on_query_finished,
                              tag_notice)
                gtk.gdk.threads_leave()
                query.execute(True)
                if query.failed:
                    # hmpf, doesn't work that way... so just return here...
                    return
#                    gtk.gdk.threads_enter()
#                    dlg = gtk.MessageDialog(None,
#                                            gtk.DIALOG_MODAL|
#                                            gtk.DIALOG_DESTROY_WITH_PARENT,
#                                            gtk.MESSAGE_ERROR,
#                                            gtk.BUTTONS_YES_NO,
#                                            _(u"An error occurred. Continue?"))
#                    if dlg.run() == gtk.RESPONSE_NO:
#                        leave = True
#                    else:
#                        leave = False
#                    dlg.destroy()
#                    gtk.gdk.threads_leave()
#                    if leave:
#                        return
        buffer = self.textview.get_buffer()
        bounds = buffer.get_selection_bounds()
        self.results.reset()
        if not bounds:
            bounds = buffer.get_bounds()
        statement = buffer.get_text(*bounds)
        if self.app.config.get("editor.replace_variables"):
            tpl = string.Template(statement)
            tpl_search = tpl.pattern.search(tpl.template)
            if tpl_search and tpl_search.groupdict().get("named"):
                dlg = StatementVariablesDialog(tpl)
                gtk.gdk.threads_enter()
                if dlg.run() == gtk.RESPONSE_OK:
                    statement = dlg.get_statement()
                else:
                    statement = None
                dlg.destroy()
                gtk.gdk.threads_leave()
                if not statement:
                    return
        def foo(connection, msg):
            self.results.add_message(msg)
        tag_notice = self.connection.connect("notice", foo)
        if self.connection.threadsafety >= 2:
            thread.start_new_thread(exec_threaded, (statement,))
        else:
            cur = self.connection.cursor()
            if self.app.config.get("sqlparse.enabled", True):
                if self.connection:
                    dialect = self.connection.sqlparse_dialect
                else:
                    dialect = None
                stmts = [unicode(x)
                         for x in sqlparse.parse(statement, dialect=dialect)]
            else:
                stms = [statement]
            for stmt in stmts:
                if not stmt.strip():
                    continue
                query = Query(stmt, cur)
                query.coding_hint = self.connection.coding_hint
                query.connect("started", self.on_query_started)
                query.connect("finished", self.on_query_finished, tag_notice)
                query.execute()

    def explain(self):
        buf = self.textview.get_buffer()
        bounds = buf.get_selection_bounds()
        if not bounds:
            bounds = buf.get_bounds()
        statement = buf.get_text(*bounds)
        if self.connection:
            dialect = self.connection.sqlparse_dialect
        else:
            dialect = None
        if len(sqlparse.parse(statement, dialect=dialect)) > 1:
            dialogs.error(_(u"Select a single statement to explain."))
            return
        data = []
        if self.connection:
            data = self.connection.explain(statement)
        self.results.set_explain(data)

    def set_connection(self, conn):
        if self.connection and self.__conn_close_tag:
            self.connection.disconnect(self.__conn_close_tag)
            self.__conn_close_tag = None
        self.connection = conn
        if conn:
            self.__conn_close_tag = self.connection.connect("closed",
                                                            self.on_connection_closed)
        else:
            self._conn_close_tag = None
        self.emit("connection-changed", conn)

    def set_filename(self, filename):
        self._filename = filename
        if filename:
            f = open(self._filename)
            a = f.read()
            f.close()
        else:
            a = ""
        self._filecontent_read = a
        self.textview.get_buffer().set_text(a)
        self.app.recent_manager.add_item(to_uri(filename))

    def get_filename(self):
        return self._filename

    def file_contents_changed(self):
        if self._filename:
            buffer = self.textview.get_buffer()
            return buffer.get_text(*buffer.get_bounds()) != self._filecontent_read
        return False

    def contents_changed(self):
        if self._filename:
            return self.file_contents_changed()
        elif len(self.get_text()) == 0:
            return False
        return True

    def file_confirm_save(self):
        dlg = dialogs.yesno(_(u"Save file %(name)s before closing the editor?") % {"name":os.path.basename(self._filename)})
        if dlg == gtk.RESPONSE_YES:
            return self.save_file_as()
        return True

    def save_file(self, parent=None, default_name=None):
        if not self._filename:
            return self.save_file_as(parent=parent, default_name=default_name)
        buffer = self.get_buffer()
        a = buffer.get_text(*buffer.get_bounds())
        f = open(self._filename, "w")
        f.write(a)
        f.close()
        self._filecontent_read = a
        gobject.idle_add(buffer.emit, "changed")
        return True

    def save_file_as(self, parent=None, default_name=None):
        if not parent:
            parent = self.instance
        dlg = gtk.FileChooserDialog(_(u"Save file"),
                            parent,
                            gtk.FILE_CHOOSER_ACTION_SAVE,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                             gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        if self._filename:
            dlg.set_filename(self._filename)
        else:
            dlg.set_current_folder(self.app.config.get("editor.recent_folder", ""))
            if default_name:
                dlg.set_current_name(default_name)
        filter = gtk.FileFilter()
        filter.set_name(_(u"All files (*)"))
        filter.add_pattern("*")
        dlg.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name(_(u"SQL files (*.sql)"))
        filter.add_pattern("*.sql")
        dlg.add_filter(filter)
        dlg.set_filter(filter)
        if dlg.run() == gtk.RESPONSE_OK:
            self._filename = dlg.get_filename()
            gobject.idle_add(self.save_file)
            self.app.config.set("editor.recent_folder", dlg.get_current_folder())
            ret = True
        else:
            ret = False
        dlg.destroy()
        return ret

    def get_buffer(self):
        return self.textview.get_buffer()

    def get_text(self):
        buffer = self.get_buffer()
        return buffer.get_text(*buffer.get_bounds())

    def set_text(self, txt):
        buffer = self.get_buffer().set_text(txt)

    def show_in_separate_window(self):
        instance = self.app.new_instance(show=False)
        instance.editor_append(self)
        instance.show()
    detach = show_in_separate_window  # make it compatible with PaneItem

    def show_in_main_window(self):
        self.instance.queries.attach(self)
        win = self.get_data("win")
        if win:
            win.destroy()
        self.set_data("win", None)

    def update_exectime(self, start, query):
        lbl = _("Query running... (%.3f seconds)" % (time.time()-start))
        self.results.add_message(lbl, path=query.path_status)
        if query.executed:
            if self._query_timer is not None:
                gobject.source_remove(self._query_timer)
            self._query_timer = None
            return False
        else:
            return True

    # Printing

    def on_print_paginate(self, operation, context, compositor):
        if compositor.paginate(context):
            n_pages = compositor.get_n_pages()
            operation.set_n_pages(n_pages)
            return True
        return False

    def on_print_draw_page(self, operation, context, page_no, compositor):
        compositor.draw_page(context, page_no)

    def on_end_page(self, operation, context, compositor):
        pass

    def print_contents(self, preview=False):
        """Send content of editor to printer."""
        view = self.textview
        compositor = gtksourceview2.print_compositor_new_from_view(view)
        operation = gtk.PrintOperation()
        operation.connect('paginate', self.on_print_paginate, compositor)
        operation.connect('draw-page', self.on_print_draw_page, compositor)
        if preview:
            action = gtk.PRINT_OPERATION_ACTION_PREVIEW
        else:
            action = gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG
        operation.run(action)


class EditorWindow(GladeWidget):

    def __init__(self, app, instance, editor=None):
        GladeWidget.__init__(self, app, "crunchyfrog", "editorwindow")
        self.instance = instance
        self.editor = None
        self.toolbar = CFToolbar(self.instance, xml="crunchyfrog",
                                 cb_provider=self)
        box = self.xml.get_widget("mainbox_editor")
        box.pack_start(self.toolbar.widget, False, False)
        box.reorder_child(self.toolbar.widget, 1)
        item = gtk.ToolButton()
        item.set_label(_(u"Show in main window"))
        item.set_stock_id("gtk-dnd-multiple")
        item.connect("clicked", self.on_show_in_main_window)
        item.show()
        self.toolbar.insert(item, -1)
        item = gtk.ToolButton()
        item.set_stock_id("gtk-close")
        item.connect("clicked", self.on_close)
        item.show()
        self.toolbar.insert(item, -1)
        self.restore_window_state()
        if editor is not None:
            self.attach(editor)

    def on_buffer_changed(self, buffer):
        gobject.idle_add(self.update_title)

    def on_close(self, *args):
        self.close()

    def on_execute_query(self, *args):
        gobject.idle_add(self.editor.execute_query)

    def on_begin_transaction(self, *args):
        gobject.idle_add(self.editor.begin_transaction)

    def on_commit(self, *args):
        gobject.idle_add(self.editor.commit)

    def on_rollback(self, *args):
        gobject.idle_add(self.editor.rollback)

    def on_query_new(self, *args):
        self.instance.on_query_new(self, *args)

    def on_open_file(self, *args):
        dlg = gtk.FileChooserDialog(_(u"Select file"),
                            self.widget,
                            gtk.FILE_CHOOSER_ACTION_OPEN,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                             gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dlg.set_current_folder(self.app.config.get("editor.recent_folder", ""))
        filter = gtk.FileFilter()
        filter.set_name(_(u"All files (*)"))
        filter.add_pattern("*")
        dlg.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name(_(u"SQL files (*.sql)"))
        filter.add_pattern("*.sql")
        dlg.add_filter(filter)
        dlg.set_filter(filter)
        if dlg.run() == gtk.RESPONSE_OK:
            gobject.idle_add(self.editor.set_filename, dlg.get_filename())
            self.app.config.set("editor.recent_folder", dlg.get_current_folder())
        dlg.destroy()

    def on_save_file(self, *args):
        self.editor.save_file(parent=self.widget)

    def on_save_file_as(self, *args):
        self.editor.save_file_as(parent=self.widget)

    def on_copy(self, *args):
        self.editor.textview.get_buffer().copy_clipboard(gtk.clipboard_get())

    def on_paste(self, *args):
        self.editor.textview.get_buffer().paste_clipboard(gtk.clipboard_get(), None, True)

    def on_cut(self, *args):
        self.editor.textview.get_buffer().cut_clipboard(gtk.clipboard_get(), True)

    def on_delete(self, *args):
        self.editor.textview.get_buffer().delete_selection(True, True)

    def on_show_in_main_window(self, *args):
        self.editor.show_in_main_window()

    def on_configure_event(self, win, event):
        config = self.app.config
        if not config.get("querywin.maximized"):
            config.set("querywin.width", event.width)
            config.set("querywin.height", event.height)

    def on_window_state_event(self, win, event):
        config = self.app.config
        bit = gtk.gdk.WINDOW_STATE_MAXIMIZED.value_names[0] in event.new_window_state.value_names
        config.set("querywin.maximized", bit)

    def attach(self, editor):
        self.editor = editor
        box = self.xml.get_widget("mainbox_editor")
        ebox = self.xml.get_widget("box_editor")
        ebox.get_parent().remove(ebox)
        if self.editor.get_parent():
            self.editor.reparent(box)
            expand, fill, padding, pack_type = box.query_child_packing(self.editor.widget)
            box.set_child_packing(self.editor.widget, True, True, padding, gtk.PACK_START)
        else:
            box.pack_start(self.editor.widget, True, True)
        box.reorder_child(self.editor.widget, 2)
        buffer = self.editor.textview.get_buffer()
        buffer.connect("changed", self.on_buffer_changed)
        self.toolbar.set_editor(editor)
        self.update_title()

    def close(self):
        self.editor.close()

    def restore_window_state(self):
        if self.app.config.get("querywin.width", -1) != -1:
            self.widget.resize(self.app.config.get("querywin.width"),
                               self.app.config.get("querywin.height"))
        if self.app.config.get("querywin.maximized", False):
            self.widget.maximize()

    def update_title(self):
        buffer = self.editor.textview.get_buffer()
        txt = buffer.get_text(*buffer.get_bounds())
        txt = re.sub("\s+", " ", txt)
        txt = txt.strip()
        if len(txt) > 28:
            txt = txt[:25]+"..."
        if txt:
            txt = _(u"Query") + ": "+txt
        else:
            txt = _(u"Query")
        self.set_title(txt)


class ResultsView(GladeWidget):

    def __init__(self, win, xml):
        self.instance = win
        GladeWidget.__init__(self, win, xml, "editor_results")

    def _setup_widget(self):
        self.grid = ResultList(self.instance, self.xml)
        self.messages = self.xml.get_widget("editor_results_messages")
        model = gtk.ListStore(str,  # 0 stock id
                              str,  # 1 message
                              str,  # 2 foreground color
                              int,  # 3 font weight
                              bool, # 4 is separator row
                              str,  # 5 font description
                              )
        model.connect("row-inserted", self._msg_model_changed)
        model.connect("row-deleted", self._msg_model_changed)
        self.messages.set_model(model)
        col = gtk.TreeViewColumn()
        renderer = gtk.CellRendererPixbuf()
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, 'stock-id', 0)
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'text', 1)
        col.add_attribute(renderer, 'foreground', 2)
        col.add_attribute(renderer, 'weight', 3)
        col.add_attribute(renderer, 'font', 5)
        self.messages.append_column(col)
        self.messages.set_row_separator_func(self._set_row_separator)
        self.explain_model = gtk.ListStore(str)
        treeview = self.xml.get_widget("editor_explain")
        treeview.set_model(self.explain_model)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=0)
        treeview.append_column(col)

    def _msg_model_changed(self, model, *args):
        tb_clear = self.xml.get_widget("tb_messages_clear")
        tb_copy = self.xml.get_widget("tb_messages_copy")
        sensitive = model.get_iter_first() is not None
        tb_clear.set_sensitive(sensitive)
        tb_copy.set_sensitive(sensitive)

    def _setup_connections(self):
        self.grid.grid.connect("selection-changed",
                               self.on_grid_selection_changed)

    def _set_row_separator(self, model, iter):
        return model.get_value(iter, 4)

    def on_copy_data(self, *args):
        gobject.idle_add(self.copy_data)

    def on_export_data(self, *args):
        gobject.idle_add(self.export_data)

    def on_messages_clear(self, *args):
        self.messages.get_model().clear()

    def on_messages_copy(self, *args):
        model = self.messages.get_model()
        iter_ = model.get_iter_first()
        plain = []
        while iter_ is not None:
            if model.get_value(iter_, 4): # Is it a separator?
                plain.append('-'*20)
            else:
                value = model.get_value(iter_, 1)
                if value is not None:
                    plain.append(value)
            iter_ = model.iter_next(iter_)
        clipboard = gtk.clipboard_get()
        clipboard.set_text('\n'.join(plain))

    def on_grid_selection_changed(self, grid, selected_cells):
        self.xml.get_widget("editor_copy_data").set_sensitive(bool(selected_cells))

    def copy_data(self):
        rows = dict()
        for cell in self.grid.grid.get_selected_cells():
            value = self.grid.grid.get_cell_data(cell, repr=True)
            if rows.has_key(cell[0]):
                rows[cell[0]] += "%s\t" % value
            else:
                rows[cell[0]] = "%s\t" % value
        rownums = rows.keys()
        rownums.sort()
        txt = ""
        for rownum in rownums:
            txt += "%s\n" % rows.get(rownum)
        display = gtk.gdk.display_manager_get().get_default_display()
        clipboard = gtk.Clipboard(display, "CLIPBOARD")
        clipboard.set_text(txt)
        self.instance.statusbar.set_message(_(u"Data copied to clipboard"))

    def export_data(self):
        data = self.grid.grid.get_grid_data()
        description = self.grid.grid.description
        selected = self.grid.grid.get_selected_rows()
        statement = self.grid.query.statement
        gtk.gdk.threads_enter()
        dlg = DataExportDialog(self.app, self.instance,
                               data, selected, statement, description)
        if dlg.run() == gtk.RESPONSE_OK:
            dlg.hide()
            dlg.export_data()
        dlg.destroy()
        gtk.gdk.threads_leave()

    def reset(self):
        # Explain
        self.explain_model.clear()
        # Messages
        # Only gray out messages from previous runs, don't remove them!
        model = self.messages.get_model()
        iter_ = model.get_iter_first()
        while iter_:
            model.set_value(iter_, 2, '#cccccc')
            iter_ = model.iter_next(iter_)
        self.set_current_page(2)

    def set_explain(self, data):
        self.explain_model.clear()
        for item in data:
            iter = self.explain_model.append()
            self.explain_model.set(iter, 0, item)

    def set_query(self, query):
        self.grid.set_query(query)
        model = self.messages.get_model()
        for err in query.errors:
            self.add_error(err.strip(), monospaced=True)
        for msg in query.messages:
            self.add_output(msg.strip())
        if query.errors:
            curr_page = 2
        elif query.description:
            curr_page = 0
        else:
            curr_page = 2
        self.xml.get_widget("editor_export_data").set_sensitive(bool(query.rows))
        gobject.idle_add(self.set_current_page, curr_page)

    def add_message(self, msg, type_=None, path=None, monospaced=False):
        """Add a message.

        Args:
          msg: The message to add.
          type_: Message type ('info', 'output',
                 'error', 'warning', 'query', None).
        """
        assert type_ in (None, 'info', 'output', 'error', 'warning', 'query')
        stock_id = None
        foreground = None
        if monospaced:
            font = 'Monospace 10'
        else:
            font = None
        weight = pango.WEIGHT_NORMAL
        if type_ == 'info':
            stock_id = 'gtk-info'
            foreground = '#336699'
        elif type_ == 'error':
            stock_id = 'gtk-dialog-error'
            foreground = '#a40000'
            weight = pango.WEIGHT_BOLD
        elif type_ == 'warning':
            stock_id = 'gtk-dialog-warning'
            foreground = '#00a400'
        elif type_ == 'query':
            stock_id ='gtk-execute'
            weight = pango.WEIGHT_BOLD
        elif type_ == 'output':
            stock_id = 'gtk-go-back'
            font = 'Monospace'
        model = self.messages.get_model()
        if model is None:  # we are in shutdown phase
            return
        msg = msg.strip()
        if path is None:
            itr = model.append([stock_id, msg, foreground, weight,
                                False, font])
        else:
            try:
                iter_ = model.get_iter(path)
            except ValueError:
                return
            model.set_value(iter_, 0, stock_id)
            model.set_value(iter_, 1, msg)
            model.set_value(iter_, 2, foreground)
            model.set_value(iter_, 3, weight)
            model.set_value(iter_, 5, font)
            itr = iter_
        # Somehow this works smarter than treeview.scroll_to_cell(path).
        # See: http://www.mail-archive.com/pygtk@daa.com.au/msg17059.html
        self.messages.scroll_to_cell(str(len(model)-1))
        self.widget.set_current_page(2)
        return model.get_path(itr)

    def add_error(self, msg, monospaced=False):
        return self.add_message(msg, 'error', monospaced=monospaced)

    def add_info(self, msg):
        return self.add_message(msg, 'info')

    def add_warning(self, msg):
        return self.add_message(msg, 'warning')

    def add_output(self, msg):
        return self.add_message(msg, 'output')

    def add_separator(self):
        model = self.messages.get_model()
        if not model.get_iter_first():
            return
        model.append([None, None, None, pango.WEIGHT_NORMAL, True, None])


class ResultList(GladeWidget):
    """Result list with toolbar"""

    def __init__(self, win, xml):
        GladeWidget.__init__(self, win, xml, "editor_results_data")
        self.instance = win
        self.query = None

    def _setup_widget(self):
        self.grid = Grid()
        self.xml.get_widget("sw_grid").add(self.grid)

    def set_query(self, query):
        self.query = query
        self.grid.reset()
        if self.query.description:
            self.grid.set_result(self.query.rows, self.query.description,
                                 self.query.coding_hint)



class StatementVariablesDialog(gtk.Dialog):

    def __init__(self, template):
        gtk.Dialog.__init__(self, _(u"Variables"),
                            None,
                            gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                             gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.template = template
        self._widgets = dict()
        self._setup_widget()

    def _setup_widget(self):
        vars = []
        found = []
        for match in self.template.pattern.finditer(self.template.template):
            name = match.groupdict().get("named")
            if not name or name.lower() in found:
                continue
            vars.append(name)
            found.append(name.lower())
        table = gtk.Table(len(vars), 2)
        table.set_row_spacings(5)
        table.set_col_spacings(7)
        for i in range(len(vars)):
            lbl = gtk.Label(vars[i])
            lbl.set_alignment(0, 0.5)
            table.attach(lbl, 0, 1, i, i+1, gtk.FILL, gtk.FILL)
            entry = gtk.Entry()
            table.attach(entry, 1, 2, i, i+1, gtk.EXPAND|gtk.FILL, gtk.FILL)
            self._widgets[vars[i]] = entry
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(table)
        sw.set_border_width(10)
        self.vbox.pack_start(sw, True, True)
        self.vbox.show_all()

    def on_value_edited(self, renderer, path, value):
        model = self.treeview.get_model()
        iter = model.get_iter(path)
        model.set_value(iter, 1, value)

    def get_statement(self):
        data = dict()
        for var, widget in self._widgets.items():
            data[var] = widget.get_text()
        return self.template.safe_substitute(data)
