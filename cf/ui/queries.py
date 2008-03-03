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
        self.popup_disable()
        self.set_property("enable-popup", False)
        self.connect("switch-page", self.on_switch_page)
        self.connect("page-removed", self.on_page_removed)
        self.connect("page-added", self.on_page_added)
        
    def on_page_added(self, notebook, child, page_num):
        gobject.idle_add(self.set_current_page, page_num)
        
    def on_page_removed(self, notebook, child, page_num):
        gobject.idle_add(self.instance.set_editor_active, child, False)
        
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
        self.popup_disable()
        self.set_property("enable-popup", False)
        
class TabLabel(gtk.EventBox):
    
    def __init__(self, editor):
        gtk.EventBox.__init__(self)
        self.label = gtk.Label(_(u"Query"))
        self.label.set_ellipsize(pango.ELLIPSIZE_END)
        self.label.set_width_chars(15)
        self.label.set_single_line_mode(True)
        self.label.set_alignment(0, 0.5)
        self.add(self.label)
        self.editor = editor
        self.connect("button-press-event", self.on_button_press_event)
        buffer = self.editor.textview.get_buffer()
        buffer.connect("changed", self.on_buffer_changed)
        self.update_label(buffer)
        self.show_all()
        
    def on_buffer_changed(self, buffer):
        gobject.idle_add(self.update_label, buffer)
        
    def on_button_press_event(self, box, event):
        if event.button == 3:
            time = event.time
            popup = gtk.Menu()
            item = gtk.MenuItem(_(u"Show in separate window"))
            item.connect("activate", self.on_show_in_separate_window)
            popup.append(item)
            sep = gtk.SeparatorMenuItem()
            sep.show()
            popup.append(sep)
            item = gtk.ImageMenuItem("gtk-close")
            item.connect("activate", self.on_close_editor)
            item.show()
            popup.append(item)
            popup.show_all()
            popup.popup( None, None, None, event.button, time)
            
    def on_close_editor(self, *args):
        self.editor.close()
            
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