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

import gtk
import gobject
import gconf
import pango

import re
import thread

from gettext import gettext as _

from cf.backends import Query
from cf.ui import GladeWidget
from cf.ui.toolbar import CFToolbar

try:
    import gtksourceview2
    USE_GTKSOURCEVIEW2 = True
except ImportError:
    import gtksourceview
    USE_GTKSOURCEVIEW2 = False

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
        GladeWidget.__init__(self, app, "crunchyfrog", "box_editor")
        self.set_data("win", None)
        self.show_all()
        
    def _setup_widget(self):
        self._setup_textview()
        self._setup_resultsgrid()
        
    def _setup_textview(self):
        if USE_GTKSOURCEVIEW2:
            self.textview = gtksourceview2.View()
            buffer = gtksourceview2.Buffer()
            self.textview.set_buffer(buffer)
            lm = gtksourceview2.language_manager_get_default()
            buffer.set_language(lm.get_language("sql"))
        else:
            self.textview = gtksourceview.SourceView()
            buffer = gtksourceview.SourceBuffer()
            self.textview.set_buffer(buffer)
            buffer.set_highlight(True)
            lm = gtksourceview.SourceLanguagesManager()
            for lang in lm.get_available_languages():
                if lang.get_id() == "SQL":
                    buffer.set_language(lang)
                    break
        self.update_textview_options()
        sw = self.xml.get_widget("sw_editor_textview")
        sw.add(self.textview)
        
    def _setup_resultsgrid(self):
        self.results = ResultsView(self.app, self.instance, self.xml)
        
    def _setup_connections(self):
        self.textview.connect("populate-popup", self.on_populate_popup)
        self.app.config.connect("changed", self.on_config_changed)
        
    def on_close(self, *args):
        if self.get_data("win"):
            self.get_data("win").close()
        else:
            self.destroy()
            
    def on_config_changed(self, config, option, value):
        if option.startswith("editor."):
            gobject.idle_add(self.update_textview_options)
        
    def on_populate_popup(self, textview, popup):
        sep = gtk.SeparatorMenuItem()
        sep.show()
        popup.append(sep)
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
        
    def on_query_finished(self, query):
        self.results.set_query(query)
        
    def on_show_in_main_window(self, *args):
        gobject.idle_add(self.show_in_main_window)
        
    def on_show_in_separate_window(self, *args):
        gobject.idle_add(self.show_in_separate_window)
        
    def execute_query(self):
        def exec_threaded():
            cur = self.connection.cursor()
            query = Query(buffer.get_text(*bounds), cur)
            query.connect("finished", self.on_query_finished)
            query.execute()
        buffer = self.textview.get_buffer()
        bounds = buffer.get_selection_bounds()
        if not bounds:
            bounds = buffer.get_bounds()
        if self.connection.threadsafety >= 2:
            thread.start_new_thread(exec_threaded, tuple())
        else:
            cur = self.connection.cursor()
            query = Query(buffer.get_text(*bounds), cur)
            query.connect("finished", self.on_query_finished)
            query.execute()
        
    def set_connection(self, conn):
        self.connection = conn
        self.emit("connection-changed", conn)
        
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
        
    def update_textview_options(self):
        conf = self.app.config
        tv = self.textview
        buffer = tv.get_buffer()
        if USE_GTKSOURCEVIEW2:
            tv.set_show_right_margin(conf.get("editor.right_margin"))
            tv.set_right_margin_position(conf.get("editor.right_margin_position"))
            buffer.set_highlight_matching_brackets(conf.get("editor.bracket_matching"))
            tv.set_tab_width(conf.get("editor.tabs_width"))
            sm = gtksourceview2.style_scheme_manager_get_default()
            scheme = sm.get_scheme(conf.get("editor.scheme"))
            buffer.set_style_scheme(scheme)
        else:
            tv.set_show_margin(conf.get("editor.right_margin"))
            #tv.set_right_margin(conf.get("editor.right_margin_position"))
            buffer.set_check_brackets(conf.get("editor.bracket_matching"))
            tv.set_tabs_width(conf.get("editor.tabs_width"))
        if conf.get("editor.wrap_text"):
            if conf.get("editor.wrap_split"):
                tv.set_wrap_mode(gtk.WRAP_CHAR)
            else:
                tv.set_wrap_mode(gtk.WRAP_WORD)
        else:
            tv.set_wrap_mode(gtk.WRAP_NONE)
        tv.set_show_line_numbers(conf.get("editor.display_line_numbers"))
        tv.set_highlight_current_line(conf.get("editor.highlight_current_line"))
        tv.set_insert_spaces_instead_of_tabs(conf.get("editor.insert_spaces"))
        tv.set_auto_indent(conf.get("editor.auto_indent"))
        if conf.get("editor.default_font"):
            client = gconf.client_get_default()
            font = client.get_string("/desktop/gnome/interface/monospace_font_name")
        else:
            font = conf.get("editor.font")
        tv.modify_font(pango.FontDescription(font))
        
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
        
    def on_query_new(self, *args):
        self.instance.on_query_new(self, *args)
        
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
        GladeWidget.__init__(self, app, xml, "editor_results")
        self.instance = instance
        self.grid = ResultsGrid(app, instance, xml)
        self.messages = self.xml.get_widget("editor_results_messages")
        buffer = self.messages.get_buffer()
        buffer.create_tag("error", foreground="#a40000", weight=pango.WEIGHT_BOLD)
    
    def set_query(self, query):
        self.grid.set_query(query)
        buffer = self.messages.get_buffer()
        buffer.set_text("")
        for err in query.errors:
            iter = buffer.get_end_iter()
            buffer.insert_with_tags_by_name(iter, err.strip()+"\n", "error")
        if query.errors:
            curr_page = 2
        elif query.description:
            curr_page = 0
        else:
            curr_page = 2
        gobject.idle_add(self.set_current_page, curr_page)
        
        
class ResultsGrid(GladeWidget):
    
    def __init__(self, app, instance, xml):
        GladeWidget.__init__(self, app, xml, "editor_results_data")
        self.instance = instance
        self.grid = self.xml.get_widget("editor_resultsgrid")
        self._idx = 0
        self._query = None
        
    def on_show_more(self, *args):
        gobject.idle_add(self.fetch_next)
        
    def on_show_all(self, *args):
        gobject.idle_add(self.fetch_all)
        
    def set_query(self, query):
        self._query = query
        while self.grid.get_columns():
            col = self.grid.get_column(0)
            self.grid.remove_column(col)
        btn_more = self.xml.get_widget("editor_results_more")
        btn_all = self.xml.get_widget("editor_results_all")
        btn_more.set_sensitive(False)
        btn_all.set_sensitive(False)
        btn_more.set_tooltip(self.instance.tt, _(u"Show next %(num)s rows") % {"num" : self.app.config.get("editor.results.offset")})
        btn_all.set_tooltip(self.instance.tt, _(u"Show all %(num)s rows") % {"num" : query.rowcount})
        if not query.description: return
        model_args = list()
        for name, type_code, display_size, internal_size, precision, scale, null_ok in query.description:
            model_args.append(str)
            col = gtk.TreeViewColumn(name.replace("_", "__"), gtk.CellRendererText(), markup=len(model_args)-1)
            self.grid.append_column(col)
        model_args.append(int)
        model_args.append(str)
        col = gtk.TreeViewColumn("#", gtk.CellRendererText(), text=len(model_args)-2, cell_background=len(model_args)-1)
        self.grid.insert_column(col, 0)
        model = gtk.ListStore(*model_args)
        self.grid.set_model(model)
        self.fetch_next()
        
    def fetch_all(self):
        while self.fetch_next():
            pass
        
    def fetch_next(self, fetch_all=False):
        model = self.grid.get_model()
        offset = self.app.config.get("editor.results.offset")
        for i in range(self._idx, self._idx+offset):
            try:
                row = [gobject.markup_escape_text(str(x)) for x in self._query.rows[i]]
                row.append(i+1)
                # FIXME: Get background color from style
                row.append("#cccccc")
                model.append(row)
            except IndexError:
                pass
        self._idx = self._idx+offset
        if self._idx > len(self._query.rows)-1:
            self._idx = len(self._query.rows)-1
        btn_more = self.xml.get_widget("editor_results_more")
        btn_all = self.xml.get_widget("editor_results_all")
        btn_more.set_sensitive(self._idx < len(self._query.rows)-1)
        btn_all.set_sensitive(self._idx < len(self._query.rows)-1)
        if fetch_all and self._idx < len(self._query.rows)-1:
            gobject.idle_add(self.fetch_next, fetch_all)
        else: 
            return (self._idx < len(self._query.rows)-1)
            
