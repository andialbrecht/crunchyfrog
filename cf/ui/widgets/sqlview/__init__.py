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

# The code for highlighting text marks is derived from the browse view
# in Giggle (http://live.gnome.org/giggle) written by
# Mathias Hasselmann <mathias@taschenorakel.de>.

import cairo
import gtk
import gtksourceview2
import gobject
import pango

try:
    import gconf
    HAVE_GCONF = True
except ImportError:
    HAVE_GCONF = False

import sqlparse


class SQLView(gtksourceview2.View):
    """SQLViewBase implementation"""

    def __init__(self, win, editor=None):
        gtksourceview2.View.__init__(self)
        gtk.widget_push_composite_child()
        self.editor = editor
        self.buffer = gtksourceview2.Buffer()
        self.set_buffer(self.buffer)
        self.set_show_line_marks(True)
        width, height = gtk.icon_size_lookup(gtk.ICON_SIZE_MENU)
        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True,
                                8, width, height)
        pixbuf.fill(0)
        self.set_mark_category_pixbuf('sql-start', pixbuf)
        self.set_mark_category_pixbuf('sql-end', pixbuf)
        lang_manager = gtksourceview2.language_manager_get_default()
        self.buffer.set_language(lang_manager.get_language('sql'))
        self.app = win.app
        self._sig_app_config_changed = self.app.config.connect(
            'changed', self.on_config_changed)
        self.update_textview_options()
        self._buffer_changed_cb = None
        self.buffer.connect('end-user-action', self.on_buffer_changed)
        self.buffer.connect('mark-set', self.on_mark_set)
        if self.editor is not None:
            self.editor.connect('connection-changed', lambda e, c:
                                self.on_buffer_changed(self.buffer))
        self.connect('expose-event', self.on_expose)
        self._sql_marks = set()
        self.connect('destroy', self.on_destroy)

    def on_buffer_changed(self, buffer):
        """Installs timeout callback to self.buffer_changed_cb()."""
        if self._buffer_changed_cb is not None:
            gobject.source_remove(self._buffer_changed_cb)
            self._buffer_changed_cb = None
        self._buffer_change_cb = gobject.idle_add(self.buffer_changed_cb,
                                                  buffer)

    def on_config_changed(self, config, option, value):
        """Updates view and buffer on configuration change."""
        if option.startswith('editor.'):
            gobject.idle_add(self.update_textview_options)
        if option == "sqlparse.enabled":
            gobject.idle_add(self.buffer_changed_cb, self.buffer)

    def on_destroy(self, *args):
        self.app.config.disconnect(self._sig_app_config_changed)

    def on_expose(self, view, event):
        left_margin = view.get_window(gtk.TEXT_WINDOW_LEFT)

        if left_margin != event.window:
            return False

        buffer_ = view.get_buffer()
        color = self.get_style().base[gtk.STATE_SELECTED]

        cr = event.window.cairo_create()
        cr.rectangle(event.area.x, event.area.y-0.5,
                     event.area.width, event.area.height)
        cr.clip()

        visible_rect = view.get_visible_rect()
        iter_ = view.get_iter_at_location(visible_rect.x, visible_rect.y)
        y, _ = view.get_line_yrange(iter_)
        offset = y-visible_rect.y
        visible_rect.y += visible_rect.height

        margin_width, _ = left_margin.get_size()
        cr.translate(margin_width-16, offset)

        forward = True
        within_statement = self._iter_in_statement(iter_.get_line())
        curr = self.get_current_statement()
        if curr:
            clstart, clend = [x.get_line() for x in curr]
        else:
            clstart = clend = None
        current = False

        while not iter_.is_end():
            y, height = view.get_line_yrange(iter_)
            if y >= visible_rect.y:
                break
            lineno = iter_.get_line()
            start = False
            end = False
            for mark in buffer_.get_source_marks_at_line(lineno, None):
                name = mark.get_category()
                if name.startswith('sql'):
                    if name.endswith('-start'):
                        within_statement = True
                        start = True
                    elif name.endswith('-end'):
                        end = True
            if clstart is not None and clend is not None:
                current = (lineno>=clstart and lineno<=clend)
            else:
                current = False
            if within_statement:
                self._render_sql_marker(cr, 16, height, color,
                                        start, end, current)
            if end == True:
                within_statement = False
                current = False
            cr.translate(0, height)
            forward = iter_.forward_line()

    def _render_sql_marker(self, cr, width, height, color,
                           start, end, current):
        if current:
            alpha = 1
        else:
            alpha = 0.5

        x0 = 2
        y0 = 0
        x1 = width - 3
        y1 = height - 1

        r = color.red / 65535.0
        g = color.green / 65535.0
        b = color.blue / 65535.0

        gradient = cairo.LinearGradient(0, 0, 0, height)

        if start:
            gradient.add_color_stop_rgba(0.0, r, g, b, 0.0 * alpha)
            gradient.add_color_stop_rgba(0.1, r, g, b, 0.3 * alpha)
            gradient.add_color_stop_rgba(0.4, r, g, b, 0.8 * alpha)
            cr.move_to(x0, y0 + 9)
            cr.curve_to(x0, y0 + 1, x0, y0 + 1, x0 + 8, y0 + 1)
            cr.line_to(x1 - 8, y0 + 1)
            cr.curve_to(x1, y0 + 1, x1, y0 + 1, x1, y0 + 9)
	else:
            gradient.add_color_stop_rgba(0.0, r, g, b, 0.6 * alpha)
            cr.move_to(x0, y0)
            cr.line_to(x1, y0)

	if end:
            gradient.add_color_stop_rgba(1.0, r, g, b, 0.0 * alpha)
            gradient.add_color_stop_rgba(0.9, r, g, b, 0.3 * alpha)
            gradient.add_color_stop_rgba(0.6, r, g, b, 0.6 * alpha)
            cr.line_to(x1, y1 - 9)
            cr.curve_to(x1, y1 - 1, x1, y1 - 1, x1 - 8, y1 - 1)
            cr.line_to(x0 + 8, y1 - 1)
            cr.curve_to(x0, y1 - 1, x0, y1 - 1, x0, y1 - 9)
	else:
            gradient.add_color_stop_rgba(1.0, r, g, b, 0.6 * alpha)
            cr.line_to(x1, y1 + 1)
            cr.line_to(x0, y1 + 1)

        cr.set_source(gradient)
	cr.fill()

	x0 += 0.5
	y0 += 0.5
	x1 += 0.5
	y1 += 0.5

        if start:
            if end:
                cr.move_to(x0, y0 + 9)
            else:
                cr.move_to(x0, y1)
                cr.line_to(x0, y0 + 8)

            cr.curve_to(x0, y0 + 1, x0, y0 + 1, x0 + 8, y0 + 1)
            cr.line_to(x1 - 8, y0 + 1)
            cr.curve_to(x1, y0 + 1, x1, y0 + 1, x1, y0 + 9)
	else:
            cr.move_to(x1, y0)

	if end:
            cr.line_to(x1, y1 - 9)
            cr.curve_to(x1, y1 - 1, x1, y1 - 1, x1 - 8, y1 - 1)
            cr.line_to(x0 + 8, y1 - 1)
            cr.curve_to(x0, y1 - 1, x0, y1 - 1, x0, y1 - 9)
	else:
            cr.line_to(x1, y1 + 1)
            cr.move_to(x0, y1)

	if not start:
            cr.line_to(x0, y0)

	cr.set_line_width(1)
	cr.set_source_rgba(r, g, b, alpha)
	cr.stroke()

    def on_mark_set(self, buffer_, iter_, mark):
        insert = buffer_.get_insert()
        if insert != mark:
            return False
        self.queue_draw()

    def _iter_in_statement(self, lineno):
        for start, end in self.get_statements():
            startl = start.get_line()
            endl = end.get_line()
            if lineno >= startl and lineno <= endl:
                return True
        return False

    def buffer_changed_cb(self, buffer):
        """Update marks."""
        # TODO(andi): Needs optimizations. Is there a way to fetch all marks?
        while self._sql_marks:
            mark = self._sql_marks.pop()
            self.buffer.delete_mark(mark)
        cursor_iter = buffer.get_iter_at_mark(buffer.get_insert())
        cursor_line = cursor_iter.get_line()
        if self.app.config.get("sqlparse.enabled", True):
            for iter_start, iter_end in self.find_statements():
                # Mark beginning of line
                iter_start.set_line_offset(0)
                iter_end.set_line_offset(0)
                mark = buffer.create_source_mark(None, 'sql-start',
                                                 iter_start)
                self._sql_marks.add(mark)
                mark = buffer.create_source_mark(None, 'sql-end', iter_end)
                self._sql_marks.add(mark)
        self._buffer_changed_cb = None
        self.queue_draw()
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
            if HAVE_GCONF:
                client = gconf.client_get_default()
                default_font = '/desktop/gnome/interface/monospace_font_name'
                font = client.get_string(default_font)
            else:
                font = 'Monospace 10'
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

    def find_statements(self):
        """Finds statements in current buffer.

        Returns:
            List of 2-tuples (start iter, end iter).
        """
        buffer_ = self.get_buffer()
        buffer_start, buffer_end = buffer_.get_bounds()
        content = buffer_.get_text(buffer_start, buffer_end)
        iter_ = buffer_.get_start_iter()
        for stmt in sqlparse.split(content):
            if not stmt.strip():
                continue
            # FIXME: Does not work if linebreaks in buffers are not '\n'.
            #    sqlparse unifies them!
            bounds = iter_.forward_search(stmt.strip(),
                                          gtk.TEXT_SEARCH_TEXT_ONLY)
            if bounds is None:
                continue
            start, end = bounds
            yield start, end
            iter_ = end
            if not iter_:
                raise StopIteration
        raise StopIteration

    def get_statements(self):
        """Returns iter 2-tuples for marked statements."""
        buffer_ = self.buffer
        iter_ = buffer_.get_iter_at_line(0)
        start = None
        end = None
        while not iter_.is_end():
            lineno = iter_.get_line()
            for mark in buffer_.get_source_marks_at_line(lineno, None):
                name = mark.get_category()
                if name.endswith('-start'):
                    start = buffer_.get_iter_at_mark(mark)
                elif name.endswith('-end'):
                    end = buffer_.get_iter_at_mark(mark)
            if start is not None and end is not None:
                end.forward_to_line_end()
                yield start, end
                start = end = None
            iter_.forward_line()
        raise StopIteration

    def get_current_statement(self):
        """Returns iters for statement where insert mark is or None."""
        iter_ = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        lineno = iter_.get_line()
        for start, end in self.get_statements():
            startl = start.get_line()
            endl = end.get_line()
            if lineno >= startl and lineno <= endl:
                return start, end
        return None
