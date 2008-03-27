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

import gtk
import gobject
import gconf
import pango
import gnome
import gnomevfs

import re
import thread
import time
import os
import string

from gettext import gettext as _

from cf.backends import Query
from cf.ui import GladeWidget
from cf.ui.toolbar import CFToolbar
from cf.ui.widgets import DataExportDialog
from cf.ui.widgets.grid import Grid
from cf.ui.widgets.sqlview import SQLView
    

class Editor(GladeWidget):
    
    __gsignals__ = {
        "connection-changed" : (gobject.SIGNAL_RUN_LAST,
                                gobject.TYPE_NONE,
                                (gobject.TYPE_PYOBJECT,))
    }
    
    def __init__(self, app, instance):
        self.app = app
        self.instance = instance
        self.connection = None
        self.__conn_close_tag = None
        self._query_timer = None
        self._filename = None
        self._filecontent_read = ""
        GladeWidget.__init__(self, app, "crunchyfrog", "box_editor")
        self.set_data("win", None)
        self.show_all()
        
    def _setup_widget(self):
        self._setup_textview()
        self._setup_resultsgrid()
        self.lbl_status = self.xml.get_widget("editor_label_status")
        
    def _setup_textview(self):
        self.textview = SQLView(self.app)
        sw = self.xml.get_widget("sw_editor_textview")
        sw.add(self.textview)
        
    def _setup_resultsgrid(self):
        self.results = ResultsView(self.app, self.instance, self.xml)
        
    def _setup_connections(self):
        self.textview.connect("populate-popup", self.on_populate_popup)
        
    def on_close(self, *args):
        self.close()
            
    def on_connection_closed(self, connection):
        if connection == self.connection and self.__conn_close_tag:
            connection.disconnect(self.__conn_close_tag)
        self.set_connection(None)
        
    def on_explain(self, *args):
        gobject.idle_add(self.explain)
        
    def on_populate_popup(self, textview, popup):
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
                item.connect("activate", self.on_show_context_help, refviewer, url)
                item.show()
                popup.append(item)
        if self.get_data("win"):
            lbl = _(u"Show in main window")
            cb = self.on_show_in_main_window
        else:
            lbl = _(u"Show in separate window")
            cb = self.on_show_in_separate_window
        item = gtk.MenuItem(lbl)
        item.connect("activate", cb)
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
        self._query_timer = gobject.timeout_add(50, self.update_exectime, start, query)
        
    def on_query_finished(self, query, tag_notice):
        self.results.set_query(query)
        if query.failed:
            gobject.idle_add(self.lbl_status.set_text, _(u"Query failed (%.3f seconds)") % query.execution_time)
        elif query.description:
            gobject.idle_add(self.lbl_status.set_text, _(u"Query finished (%.3f seconds, %s rows)") % (query.execution_time, query.rowcount))
        else:
            gobject.idle_add(self.lbl_status.set_text, _(u"Query finished (%.3f seconds, %s affected rows)") % (query.execution_time, query.rowcount))
        self.connection.disconnect(tag_notice)
        gobject.idle_add(self.textview.grab_focus)
        
    def on_show_context_help(self, menuitem, refviewer, url):
        refviewer.load_url(url)
        
    def on_show_in_main_window(self, *args):
        gobject.idle_add(self.show_in_main_window)
        
    def on_show_in_separate_window(self, *args):
        gobject.idle_add(self.show_in_separate_window)
        
    def close(self):
        if self.get_data("win"):
            self.get_data("win").close()
        else:
            self.destroy()
        
    def commit(self):
        if not self.connection: return
        cur = self.connection.cursor()
        cur.execute("commit")
        cur.close()
        
    def rollback(self):
        if not self.connection: return
        cur = self.connection.cursor()
        cur.execute("rollback")
        cur.close()
        
    def begin_transaction(self):
        if not self.connection: return
        cur = self.connection.cursor()
        cur.execute("begin")
        cur.close()
        
    def execute_query(self):
        self.lbl_status.set_text(_(u"Executing query..."))
        def exec_threaded(statement):
            cur = self.connection.cursor() 
            query = Query(statement, cur)
            gtk.gdk.threads_enter()
            query.connect("started", self.on_query_started)
            query.connect("finished", self.on_query_finished, tag_notice)
            gtk.gdk.threads_leave()
            query.execute(True)
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
                    self.lbl_status.set_text(_(u"Query cancelled"))
                    return
        def foo(connection, msg):
            self.results.add_message(msg)
        tag_notice = self.connection.connect("notice", foo)
        if self.connection.threadsafety >= 2:
            thread.start_new_thread(exec_threaded, (statement,))
        else:
            cur = self.connection.cursor()
            query = Query(statement, cur)
            query.connect("finished", self.on_query_finished, tag_notice)
            query.execute()
            
    def explain(self):
        buffer = self.textview.get_buffer()
        bounds = buffer.get_selection_bounds()
        if not bounds:
            bounds = buffer.get_bounds()
        statement = buffer.get_text(*bounds)
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
            self.__conn_close_tag = self.connection.connect("closed", self.on_connection_closed)
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
        
    def get_filename(self):
        return self._filename
    
    def file_contents_changed(self):
        if self._filename:
            buffer = self.textview.get_buffer()
            return buffer.get_text(*buffer.get_bounds()) != self._filecontent_read
        return False
    
    def save_file(self, parent=None):
        if not self._filename:
            return self.save_file_as(parent=parent)
        buffer = self.get_buffer()
        a = buffer.get_text(*buffer.get_bounds())
        f = open(self._filename, "w")
        f.write(a)
        f.close()
        self._filecontent_read = a
        gobject.idle_add(buffer.emit, "changed")
        
    def save_file_as(self, parent=None):
        if not parent:
            parent = self.instance.widget
        dlg = gtk.FileChooserDialog(_(u"Save file"),
                            parent,
                            gtk.FILE_CHOOSER_ACTION_SAVE,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                             gtk.STOCK_SAVE, gtk.RESPONSE_OK))
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
            self._filename = dlg.get_filename()
            gobject.idle_add(self.save_file)
            self.app.config.set("editor.recent_folder", dlg.get_current_folder())
        dlg.destroy()
    
    def get_buffer(self):
        return self.textview.get_buffer()
    
    def get_text(self):
        buffer = self.get_buffer()
        return buffer.get_text(*buffer.get_bounds())
    
    def set_text(self, txt):
        buffer = self.get_buffer().set_text(txt)
        
    def show_in_separate_window(self):
        win = EditorWindow(self.app, self.instance)
        win.attach(self)
        win.show_all()
        self.set_data("win", win)
        
    def show_in_main_window(self):
        self.instance.queries.attach(self)
        win = self.get_data("win")
        if win:
            win.destroy()
        self.set_data("win", None)
        
    def update_exectime(self, start, query):
        self.lbl_status.set_text("Query running... (%.3f seconds)" % (time.time()-start))
        if query.executed:
            gobject.source_remove(self._query_timer)
            self._query_timer = None
            if query.failed:
                gobject.idle_add(self.lbl_status.set_text, _(u"Query failed (%.3f seconds)") % query.execution_time)
            elif query.description:
                gobject.idle_add(self.lbl_status.set_text, _(u"Query finished (%.3f seconds, %s rows)") % (query.execution_time, query.rowcount))
            else:
                gobject.idle_add(self.lbl_status.set_text, _(u"Query finished (%.3f seconds, %s affected rows)") % (query.execution_time, query.rowcount))
            return False
        else:
            return True

        
class EditorWindow(GladeWidget):
    
    def __init__(self, app, instance):
        GladeWidget.__init__(self, app, "crunchyfrog", "editorwindow")
        self.instance = instance
        self.editor = None
        self.toolbar = CFToolbar(self.app, "crunchyfrog", cb_provider=self)
        box = self.xml.get_widget("mainbox_editor")
        box.pack_start(self.toolbar.widget, False, False)
        box.reorder_child(self.toolbar.widget, 1)
        quit = self.toolbar.xml.get_widget("tb_quit")
        self.toolbar.widget.remove(quit)
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
        self.toolbar.set_icon_size(gtk.ICON_SIZE_MENU)
        self.restore_window_state()
        
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
        self.destroy()
        
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
    
    def __init__(self, app, instance, xml):
        self.instance = instance
        GladeWidget.__init__(self, app, xml, "editor_results")
        
    def _setup_widget(self):
        self.grid = ResultList(self.app, self.instance, self.xml)
        self.messages = self.xml.get_widget("editor_results_messages")
        buffer = self.messages.get_buffer()
        buffer.create_tag("error", foreground="#a40000", weight=pango.WEIGHT_BOLD)
        self.explain_model = gtk.ListStore(str)
        treeview = self.xml.get_widget("editor_explain")
        treeview.set_model(self.explain_model)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=0)
        treeview.append_column(col)
        
    def _setup_connections(self):
        self.grid.grid.connect("selection-changed", self.on_grid_selection_changed)
        
    def on_copy_data(self, *args):
        gobject.idle_add(self.copy_data)
        
    def on_export_data(self, *args):
        gobject.idle_add(self.export_data)
        
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
        dlg = DataExportDialog(self.app, self.instance.widget, 
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
        buffer = self.messages.get_buffer()
        buffer.set_text("")
        self.set_current_page(2)
        
    def set_explain(self, data):
        self.explain_model.clear()
        for item in data:
            iter = self.explain_model.append()
            self.explain_model.set(iter, 0, item)
    
    def set_query(self, query):
        self.grid.set_query(query)
        buffer = self.messages.get_buffer()
        for err in query.errors:
            iter = buffer.get_end_iter()
            buffer.insert_with_tags_by_name(iter, err.strip()+"\n", "error")
        for msg in query.messages:
            buffer.insert_at_cursor(msg.strip()+"\n")
        if query.errors:
            curr_page = 2
        elif query.description:
            curr_page = 0
        else:
            curr_page = 2
        self.xml.get_widget("editor_export_data").set_sensitive(bool(query.rows))
        gobject.idle_add(self.set_current_page, curr_page)
        
    def add_message(self, msg):
        buffer = self.messages.get_buffer()
        buffer.insert_at_cursor(msg.strip()+"\n")



class ResultList(GladeWidget):
    """Result list with toolbar"""
    
    def __init__(self, app, instance, xml):
        GladeWidget.__init__(self, app, xml, "editor_results_data")
        self.instance = instance
        self.query = None
        
    def _setup_widget(self):
        self.grid = Grid()
        self.xml.get_widget("sw_grid").add(self.grid)
        
    def set_query(self, query):
        self.query = query
        self.grid.reset()
        if self.query.description:
            self.grid.set_result(self.query.rows, self.query.description)

            

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