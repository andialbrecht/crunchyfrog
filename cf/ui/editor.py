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

from cf.db import Query
from cf.plugins.core import PLUGIN_TYPE_EXPORT
from cf.ui import dialogs
from cf.ui.confirmsave import ConfirmSaveDialog
from cf.ui.pane import PaneItem
from cf.ui.widgets import DataExportDialog
from cf.ui.widgets.grid import Grid
from cf.ui.widgets.sqlview import SQLView
from cf.utils import to_uri

import sqlparse


FORMATTER_DEFAULT_OPTIONS = {
    'reindent': True,
    'n_indents': 4,
    'keyword_case': 'upper',
    'identifier_case': 'lower',
#    'right_margin': 79
}


class Editor(gobject.GObject, PaneItem):
    """SQL editor widget.

    :Signals:

    connection-changed
      ``def callback(editor, connection)``

      Emitted when a connection was assigned to this editor.
    """

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
        """Constructor.

        :param win: A MainWindow instance.
        """
        self.__gobject_init__()
        PaneItem.__init__(self, win.app)
        self.app = win.app
        self.win = win
        self.connection = None
        self._buffer_dirty = False
        self.__conn_close_tag = None
        self._query_timer = None
        self._filename = None
        self._filecontent_read = ""
        self.builder = gtk.Builder()
        self.builder.set_translation_domain('crunchyfrog')
        self.builder.add_from_file(self.app.get_glade_file('editor.glade'))
        self.widget = self.builder.get_object('box_editor')
        self._setup_widget()
        self._setup_connections()
        self.on_messages_copy = self.results.on_messages_copy
        self.on_messages_clear = self.results.on_messages_clear
        self.on_copy_data = self.results.on_copy_data
        self.on_export_data = self.results.on_export_data
        self.builder.connect_signals(self)
        self.set_data("win", None)
        self.win.emit('editor-created', self)
        self.show_all()

    def show_all(self):
        self.widget.show_all()

    def show(self):
        self.widget.show()

    def destroy(self):
        self.widget.destroy()

    def get_widget(self):
        return self.widget

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
        sw = self.builder.get_object("sw_editor_textview")
        sw.add(self.textview)
        self.textview.buffer.connect('changed', self.on_buffer_changed)

    def _setup_resultsgrid(self):
        self.results = ResultsView(self.win, self.builder)

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
        self.win.statusbar.pop(1)
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
        self.win.statusbar.push(1, msg)
        if self.connection.handler_is_connected(tag_notice):
            self.connection.disconnect(tag_notice)
        self.textview.grab_focus()

    def on_show_in_main_window(self, *args):
        gobject.idle_add(self.show_in_main_window)

    def on_show_in_separate_window(self, *args):
        gobject.idle_add(self.show_in_separate_window)

    # Public methods

    def get_focus_child(self):
        return self.get_child1().get_children()[0].grab_focus()

    def close(self, force=False):
        """Close editor, displays a confirmation dialog for unsaved files.

        Args:
          force: If True, the method doesn't check for changed contents.
        """
        if self.contents_changed() and not force:
            dlg = ConfirmSaveDialog(self.win, [self])
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
            self.win.set_editor_active(self, False)
            self.win.editor_remove(self)
            return True

    def commit(self):
        """Commit current transaction, if any."""
        if not self.connection: return
        self.connection.commit()
        self.results.add_message('COMMIT', 'info')

    def rollback(self):
        """Commit current transaction, if any."""
        if not self.connection: return
        self.connection.rollback()
        self.results.add_message('ROLLBACK', 'info')

    def begin_transaction(self):
        """Begin transaction."""
        if not self.connection: return
        self.connection.begin()
        self.results.add_message('BEGIN TRANSACTION', 'info')

    def execute_query(self, statement_at_cursor=False):
        def exec_threaded(statement):
            if self.app.config.get("sqlparse.enabled", True):
                stmts = sqlparse.split(statement)
            else:
                stmts = [statement]
            for stmt in stmts:
                if not stmt.strip():
                    continue
                query = Query(stmt, self.connection)
#                query.coding_hint = self.connection.coding_hint
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
        self.results.reset()
        if not statement_at_cursor:
            bounds = buffer.get_selection_bounds()
            if not bounds:
                bounds = buffer.get_bounds()
        else:
            bounds = self.textview.get_current_statement()
            if bounds is None:
                return
        statement = buffer.get_text(*bounds)
        if self.app.config.get("editor.replace_variables"):
            tpl = string.Template(statement)
            tpl_search = tpl.pattern.search(tpl.template)
            if tpl_search and tpl_search.groupdict().get("named"):
                dlg = StatementVariablesDialog(tpl)
                if dlg.run() == gtk.RESPONSE_OK:
                    statement = dlg.get_statement()
                else:
                    statement = None
                dlg.destroy()
                if not statement:
                    return
        def foo(connection, msg):
            self.results.add_message(msg)
        tag_notice = self.connection.connect("notice", foo)
        if self.connection.threadsafety >= 2:
            thread.start_new_thread(exec_threaded, (statement,))
        else:
            if self.app.config.get("sqlparse.enabled", True):
                stmts = sqlparse.split(statement)
            else:
                stmts = [statement]
            for stmt in stmts:
                if not stmt.strip():
                    continue
                query = Query(stmt, self.connection)
#                query.coding_hint = self.connection.coding_hint
                query.connect("started", self.on_query_started)
                query.connect("finished", self.on_query_finished, tag_notice)
                query.execute()

    def explain(self):
        buf = self.textview.get_buffer()
        bounds = buf.get_selection_bounds()
        if not bounds:
            bounds = buf.get_bounds()
        statement = buf.get_text(*bounds)
        if len(sqlparse.split(statement)) > 1:
            dialogs.error(_(u"Select a single statement to explain."))
            return
        if not self.connection:
            return
        queries = [Query(stmt, self.connection)
                   for stmt in self.connection.explain_statements(statement)]
        def _execute_next(last, queries):
            if last is not None and last.failed:
                self.results.set_explain_results(last)
                return
            q = queries.pop(0)
            if len(queries) == 0:
                q.connect('finished',
                          lambda x: self.results.set_explain_results(x))
            else:
                q.connect('finished',
                          lambda x: _execute_next(x, queries))
            q.execute()
        _execute_next(None, queries)

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

    def get_connection(self):
        """Returns the connection assigned to the editor."""
        return self.connection

    def set_filename(self, filename):
        """Opens filename.

        Returns ``True`` if the file was successfully opened.
        Otherwise ``False``.
        """
        msg = None
        if not os.path.isfile(filename):
            msg = _(u'No such file: %(name)s')
        elif not os.access(filename, os.R_OK):
            msg = _(u'File is not readable: %(name)s')
        if msg is not None:
            dialogs.error(_(u"Failed to open file"), msg % {'name': filename})
            return False
        self._filename = filename
        if filename:
            f = open(self._filename)
            a = f.read()
            f.close()
        else:
            a = ""
        self._filecontent_read = a
        self.set_text(a)
        self.app.recent_manager.add_item(to_uri(filename))
        return True

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
        self.app.recent_manager.add_item(to_uri(self._filename))
        self._filecontent_read = a
        gobject.idle_add(buffer.emit, "changed")
        return True

    def save_file_as(self, parent=None, default_name=None):
        if not parent:
            parent = self.win
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
            self.save_file()
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
        buffer_ = self.get_buffer()
        buffer_.begin_user_action()
        buffer_.set_text(txt)
        buffer_.end_user_action()  # starts tagging of statements too

    def show_in_separate_window(self):
        instance = self.app.new_instance(show=False)
        instance.editor_append(self)
        instance.show()
    detach = show_in_separate_window  # make it compatible with PaneItem

    def show_in_main_window(self):
        self.win.queries.attach(self)
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

    # Clipboard functions

    def clipboard_copy(self, clipboard):
        """Copies selected data to clipboard.

        This is either the selected text from the editor or the selected
        cells from the results grid.
        """
        if self.textview.is_focus():
            buffer_ = self.textview.get_buffer()
            buffer_.copy_clipboard(clipboard)
        elif self.results.grid.grid.is_focus():
            self.results.clipboard_copy(clipboard)

    def clipboard_cut(self, clipboard):
        """Cuts selected text from editor."""
        buffer_ = self.textview.get_buffer()
        buffer_.cut_clipboard(clipboard, True)

    def clipboard_paste(self, clipboard):
        """Pastes clipboard data to editor."""
        buffer_ = self.textview.get_buffer()
        buffer_.paste_clipboard(clipboard, None, True)

    # Statement navigation and formatting

    def rjump_to_statement(self, offset):
        """Jumps to a statement relative to current.

        :param offset: Position relative to current statement as integer.
        """
        idx_current = 0
        positions = []
        curr = self.textview.get_current_statement()
        buffer_ = self.textview.get_buffer()
        if curr is not None:
            # We're using the presence of an end iter as a flag if we're
            # inside a statement. If not, just jump to the next/prev statement
            # without respecting the offset.
            cstart, inside_statement = curr
        else:
            cstart = buffer_.get_iter_at_mark(buffer_.get_insert())
            cstart.set_line_offset(0)
            inside_statement = None
        for start, end in self.textview.get_statements():
            positions.append((start, end))
            if not inside_statement:
                if offset > 0 and start.get_line() > cstart.get_line():
                    buffer_.place_cursor(start)
                    return
                elif offset < 0 and start.get_line() > cstart.get_line():
                    if len(positions) > 2:
                        buffer_.place_cursor(positions[-2][0])
                    elif positions:  # there's just one statement buffered
                        buffer_.place_cursor(positions[0][0])
                    return
            elif start.equal(cstart):
                idx_current = len(positions)-1
        max_idx = len(positions)-1
        if offset > 0:
            new_pos = min(idx_current+offset, max_idx)
        else:
            new_pos = max(idx_current+offset, 0)
        buffer_.place_cursor(positions[new_pos][0])

    def selected_lines_toggle_comment(self):
        """Comments/uncomments selected lines."""
        buffer_ = self.textview.get_buffer()
        res = buffer_.get_selection_bounds()
        if not res:
            start = buffer_.get_iter_at_mark(buffer_.get_insert())
            lno_start = lno_end = start.get_line()
        else:
            start, end = res
            lno_start = start.get_line()
            lno_end = end.get_line()
        buffer_.begin_user_action()
        for line_no in xrange(lno_start, lno_end+1):
            lstart = buffer_.get_iter_at_line(line_no)
            lend = lstart.copy()
            lend.forward_to_line_end()
            line = buffer_.get_text(lstart, lend)
            if not line.startswith('-- '):
                line = '-- %s' % line
            else:
                line = re.sub(r'^\s*-- ', '', line)
            buffer_.delete(lstart, lend)
            buffer_.insert(lstart, line)
        buffer_.end_user_action()

    def selected_lines_quick_format(self, **options):
        """Runs format without any other options than the default ones."""
        if not options:
            options = FORMATTER_DEFAULT_OPTIONS
        buffer_ = self.textview.get_buffer()
        res = buffer_.get_selection_bounds()
        if not res:
            start, end = buffer_.get_bounds()
            select_range = False
        else:
            start, end = res
            select_range = True
        orig = buffer_.get_text(start, end)
        formatted = sqlparse.format(orig, **options)
        # Modify buffer
        buffer_.begin_user_action()
        buffer_.delete(start, end)
        buffer_.insert(start, formatted)
        # Set selection again
        if select_range:
            end = start.copy()
            end.backward_chars(len(formatted))
            buffer_.select_range(end, start)
        buffer_.end_user_action()


class ResultsView(object):

    def __init__(self, win, builder):
        self.instance = win
        self.app = win.app
        self.widget = builder.get_object('editor_results')
        self.builder = builder
        self._setup_widget()
        self._setup_connections()

    def _setup_widget(self):
        self.grid = ResultList(self.instance, self.builder)
        self.messages = self.builder.get_object("editor_results_messages")
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
        self.explain_results = Grid()
        sw = self.builder.get_object('sw_explain_results')
        sw.add(self.explain_results)
        self.explain_results.show_all()
        self._update_btn_export_state()

    def _update_btn_export_state(self):
        """Update state of export button."""
        btn_export = self.builder.get_object('editor_export_data')
        rows = None
        if self.grid.query:
            rows = self.grid.query.rows
        sensitive = False
        if rows:
            sensitive = True
            exp_plugins = self.app.plugins.get_plugins(PLUGIN_TYPE_EXPORT,
                                                       True)
            if not exp_plugins:
                sensitive = False
        btn_export.set_sensitive(sensitive)

    def _msg_model_changed(self, model, *args):
        tb_clear = self.builder.get_object("tb_messages_clear")
        tb_copy = self.builder.get_object("tb_messages_copy")
        sensitive = model.get_iter_first() is not None
        tb_clear.set_sensitive(sensitive)
        tb_copy.set_sensitive(sensitive)

    def _setup_connections(self):
        self.grid.grid.connect("selection-changed",
                               self.on_grid_selection_changed)
        self.app.plugins.connect('plugin-added',
                                 lambda *a: self._update_btn_export_state())
        self.app.plugins.connect('plugin-removed',
                                 lambda *a: self._update_btn_export_state())
        self.app.plugins.connect('plugin-active',
                                 lambda *a: self._update_btn_export_state())

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
        self.builder.get_object("editor_copy_data").set_sensitive(bool(selected_cells))

    def copy_data(self, clipboard=None):
        """Copy selected values to clipboard.

        Columns are terminated by \t, rows by \n.
        If *clipboard* is ``None``, the default clipboard will be used.
        """
        rows = {}
        for cell in self.grid.grid.get_selected_cells():
            value = self.grid.grid.get_cell_data(cell, repr=True)
            if rows.has_key(cell[0]):
                rows[cell[0]] += "\t%s" % value
            else:
                rows[cell[0]] = "%s" % value
        rownums = rows.keys()
        rownums.sort()
        txt = "\n".join(rows.get(rownum) for rownum in rownums)
        if clipboard is None:
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
        dlg = DataExportDialog(self.instance.app, self.instance,
                               data, selected, statement, description)
        if dlg.run() == gtk.RESPONSE_OK:
            dlg.hide()
            dlg.export_data()
        dlg.destroy()
        gtk.gdk.threads_leave()

    def clipboard_copy(self, clipboard):
        """Copies selected cells to clipboard."""
        # TODO: Cleanup API. There should be one function to do this.
        self.copy_data(clipboard)

    def reset(self):
        # Explain
        self.explain_results.reset()
        # Messages
        # Only gray out messages from previous runs, don't remove them!
        model = self.messages.get_model()
        iter_ = model.get_iter_first()
        while iter_:
            model.set_value(iter_, 2, '#cccccc')
            iter_ = model.iter_next(iter_)
        self.widget.set_current_page(2)

    def set_explain_results(self, query):
        self.explain_results.reset()
        if query.failed:
            dialogs.error(_(u'Failed'), '\n'.join(query.errors),
                          parent=self.instance)
        else:
            self.explain_results.set_result(query.rows, query.description)

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
        self._update_btn_export_state()
        gobject.idle_add(self.widget.set_current_page, curr_page)

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


class ResultList(object):
    """Result list with toolbar"""

    def __init__(self, win, builder):
        self.builder = builder
        self.widget = self.builder.get_object('editor_results_data')
        self._setup_widget()
        self.instance = win
        self.query = None

    def _setup_widget(self):
        self.grid = Grid()
        self.builder.get_object("sw_grid").add(self.grid)

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
