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

"""SQL-specific TextView

This module provides a SQL-specific TextView widget. Depending on
your system it is a gtksourceview2 or gtksourceview implementation.

Both implementations inherit ``SQLViewBase`` which connects to the
configuration instance to update some options when they are changed
through the preferences dialog.

Example usage
=============

    .. sourcecode:: python

        >>> from cf.ui.widgets.sqlview import SQLView
        >>> import gtk
        >>> w = gtk.Window()
        >>> sw = gtk.ScrolledWindow()
        >>> view = SQLView(app)
        >>> view.get_buffer().set_text("select * from foo")
        >>> sw.add(view)
        >>> w.add(sw)
        >>> w.show_all()

"""

import gconf
import gtk
import gtksourceview2
import gobject
import pango

from cf import sqlparse


class SQLView(gtksourceview2.View):
    """SQLViewBase implementation"""

    def __init__(self, app, editor=None):
        gtksourceview2.View.__init__(self)
        self.editor = editor
        self.buffer = gtksourceview2.Buffer()
        self.set_buffer(self.buffer)
        self.set_show_line_marks(True)
        pixbuf = self.render_icon(gtk.STOCK_GO_FORWARD,
                                  gtk.ICON_SIZE_MENU)
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        pixbuf = pixbuf.scale_simple(width/2, height/2,
                                     gtk.gdk.INTERP_BILINEAR)
        self.set_mark_category_pixbuf('sql', pixbuf)
        lang_manager = gtksourceview2.language_manager_get_default()
        self.buffer.set_language(lang_manager.get_language('sql'))
        self.app = app
        self.app.config.connect('changed', self.on_config_changed)
        self.update_textview_options()
        self._buffer_changed_cb = None
        self.buffer.connect('changed', self.on_buffer_changed)
        if self.editor is not None:
            self.editor.connect('connection-changed', lambda e, c:
                                self.on_buffer_changed(self.buffer))
        self._sql_marks = []

    def on_buffer_changed(self, buffer):
        """Installs timeout callback to self.buffer_changed_cb()."""
        if self._buffer_changed_cb is not None:
            gobject.source_remove(self._buffer_changed_cb)
            self._buffer_changed_cb = None
        self._buffer_changed_cb = gobject.timeout_add(500,
                                                      self.buffer_changed_cb,
                                                      buffer)

    def on_config_changed(self, config, option, value):
        """Updates view and buffer on configuration change."""
        if option.startswith('editor.'):
            gobject.idle_add(self.update_textview_options)
        if option == "sqlparse.enabled":
            gobject.idle_add(self.buffer_changed_cb, self.buffer)

    def buffer_changed_cb(self, buffer):
        """Update marks."""
        # TODO(andi): Needs optimizations.
        while self._sql_marks:
            mark = self._sql_marks.pop()
            self.buffer.delete_mark(mark)
        if self.app.config.get("sqlparse.enabled", True):
            for iter_start, iter_end in self.get_statements():
                mark = buffer.create_source_mark(None, 'sql', iter_start)
                mark.set_visible(True)
                self._sql_marks.append(mark)
        self._buffer_changed_cb = None
        return False

    def update_textview_options(self):
        c = self.app.config
        buf = self.get_buffer()
        if c.get('editor.wrap_text'):
            if c.get('editor.wrap_split'):
                self.set_wrap_mode(gtk.WRAP_CHAR)
            else:
                self.set_wrap_mode(gtk.WRAP_WORD)
        else:
            self.set_wrap_mode(gtk.WRAP_NONE)
        self.set_show_line_numbers(c.get('editor.display_line_numbers'))
        self.set_highlight_current_line(c.get('editor.highlight_current_line'))
        self.set_insert_spaces_instead_of_tabs(c.get('editor.insert_spaces'))
        self.set_auto_indent(c.get('editor.auto_indent'))
        if c.get('editor.default_font'):
            client = gconf.client_get_default()
            default_font = '/desktop/gnome/interface/monospace_font_name'
            font = client.get_string(default_font)
        else:
            font = c.get('editor.font')
        self.modify_font(pango.FontDescription(font))
        self.set_show_right_margin(c.get('editor.right_margin'))
        self.set_right_margin_position(c.get('editor.right_margin_position'))
        buf.set_highlight_matching_brackets(c.get('editor.bracket_matching'))
        self.set_tab_width(c.get('editor.tabs_width'))
        sm = gtksourceview2.style_scheme_manager_get_default()
        scheme = sm.get_scheme(c.get('editor.scheme'))
        buf.set_style_scheme(scheme)

    def get_statements(self):
        """Finds statements in current buffer.

        Returns:
            List of 2-tuples (start iter, end iter).
        """
        content = self.buffer.get_text(*self.buffer.get_bounds())
        iter = self.buffer.get_start_iter()
        if self.editor and self.editor.connection:
            dialect = self.editor.connection.get_dialect()
        else:
            dialect = None
        for stmt in sqlparse.sqlsplit(content, dialect=dialect):
            start, end = iter.forward_search(stmt.lstrip(),
                                             gtk.TEXT_SEARCH_TEXT_ONLY)
            yield start, end
            iter = end
            if not iter:
                raise StopIteration
