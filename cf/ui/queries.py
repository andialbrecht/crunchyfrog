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

"""Notebook that holds SQL editors"""

import gtk
import gobject
import pango

import re
import os

from gettext import gettext as _

class QueriesNotebook(gtk.Notebook):

    def __init__(self, app, instance):
        self.app = app
        self.instance = instance
        gtk.Notebook.__init__(self)
        self.set_scrollable(True)
        self.popup_disable()
        self.set_property("enable-popup", False)
        self.connect("switch-page", self.on_switch_page)
        self.connect("page-removed", self.on_page_removed)
        def foo(notebook, context):
            dest_window = context.dest_window
            if dest_window == self.instance:
                return
            for win in self.app.get_instances():
                print win, dest_window
                if win != self.instance and win == dest_window:
                    win.editor_append(self.get_editor_by_pagenum(notebook.props.page))
                    return
            editor = self.get_editor_by_pagenum(notebook.props.page)
            editor.show_in_separate_window()
        #self.connect('drag-end', foo)
        def bar(widget, context, x, y, timestamp):
            print widget, context, x, y
        self.connect('drag-drop', bar)

    def on_page_added(self, notebook, child, page_num):
        gobject.idle_add(self.set_current_page, page_num)

    def on_page_removed(self, notebook, child, page_num):
        self.instance.set_editor_active(child, False)

    def on_switch_page(self, notebook, page, page_num):
        editor = self.get_nth_page(page_num).get_data("glade-widget")
        gobject.idle_add(self.instance.set_editor_active, editor, True)

    def attach(self, editor):
        if editor.get_parent():
            editor.reparent(self)
            self.set_tab_label(editor.widget, TabLabel(editor))
        else:
            self.append_page(editor.widget, TabLabel(editor))
        self.set_tab_reorderable(editor.widget, True)
        self.set_tab_detachable(editor.widget, True)
        self.set_current_page(self.page_num(editor.widget))

    def get_editor_by_pagenum(self, page_num):
        child = self.get_nth_page(page_num)
        lbl = self.get_tab_label(child)
        return lbl.editor


class TabLabel(gtk.HBox):

    def __init__(self, editor):
        gtk.HBox.__init__(self)
        self.label = gtk.Label(_(u"Query"))
        self.label.set_ellipsize(pango.ELLIPSIZE_END)
        self.label.set_width_chars(15)
        self.label.set_single_line_mode(True)
        self.label.set_alignment(0, 0.5)
        # use a slightly smaller font in tabs like Empathy does...
        font_desc = self.label.get_style().font_desc
        font_desc.set_size(int(font_desc.get_size()*.8))
        self.label.modify_font(font_desc)
        self.editor = editor
        self.editor.connect("connection-changed",
                            self.on_editor_connection_changed)
        buffer = self.editor.textview.get_buffer()
        buffer.connect("changed", self.on_buffer_changed)
        self.update_label(buffer)
        self.pack_start(self.label, True, True)
        btn_close = gtk.Button()
        btn_close.connect("clicked", self.on_button_close_clicked)
        self.add_icon_to_button(btn_close)
        btn_close.set_relief(gtk.RELIEF_NONE)
        self.pack_start(btn_close, False, False)
        self.update_tooltip()
        self.show_all()

    def add_icon_to_button(self,button):
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_CLOSE,gtk.ICON_SIZE_MENU)
        button.set_relief(gtk.RELIEF_NONE)
        button.set_image(image)
        settings = gtk.Widget.get_settings(image)
        (w,h) = gtk.icon_size_lookup_for_settings(settings,gtk.ICON_SIZE_MENU)
        button.set_size_request(w+12, h+6)
        button.set_border_width(0)
        image.show()
        return

    def on_button_close_clicked(self, button):
        self.editor.close()

    def on_buffer_changed(self, buffer):
        gobject.idle_add(self.update_label, buffer)

    def on_close_editor(self, *args):
        self.editor.close()

    def on_editor_connection_changed(self, editor, connection):
        self.update_tooltip()

    def on_show_in_separate_window(self, item):
        gobject.idle_add(self.editor.show_in_separate_window)

    def update_label(self, buffer):
        if self.editor.get_filename():
            fname = self.editor.get_filename()
            txt = os.path.split(fname)[-1]
            self.label.set_tooltip_text(fname)
            if self.editor.file_contents_changed():
                txt = "*"+txt
        else:
            self.label.set_tooltip_text("")
            txt = buffer.get_text(*buffer.get_bounds())
            txt = re.sub("\s+", " ", txt)
        txt = txt.strip()
        if not txt:
            txt = _(u"Query")
        self.label.set_text(txt)
        self.update_tooltip()

    def update_tooltip(self):
        markup = "<b>Connection:</b> "
        if self.editor.connection:
            markup += self.editor.connection.get_label()
        else:
            markup += "["+_(u"Not connected")+"]"
        if self.editor.get_filename():
            markup += "\n<b>File:</b> "+self.editor.get_filename()
        self.label.set_tooltip_markup(markup)

