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

import os

from gettext import gettext as _

from cf.ui import GladeWidget

MODE_SINGLE = 1
MODE_MULTIPLE = 2

class ConfirmSaveDialog(GladeWidget):
    
    def __init__(self, instance, changed_editors):
        GladeWidget.__init__(self, instance.app, "crunchyfrog",
                             "saveconfirm_dialog")
        self.changed_editors = changed_editors
        if len(changed_editors) == 1:
            self.set_dialog_mode(MODE_SINGLE)
        else:
            self.set_dialog_mode(MODE_MULTIPLE)
        self.fill_filelist()
        
    def _setup_widget(self):
        model = gtk.ListStore(gobject.TYPE_PYOBJECT, str, bool, str)
        self.filelist = self.xml.get_widget("filelist")
        self.filelist.set_model(model)
        self.filelist.set_tooltip_column(3)
        col = gtk.TreeViewColumn()
        renderer = gtk.CellRendererToggle()
        renderer.connect("toggled", self.on_entry_toggled)
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, "active", 2)
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'text', 1)
        self.filelist.append_column(col)
        
    def on_entry_toggled(self, renderer, path):
        model = self.filelist.get_model()
        iter = model.get_iter(path)
        model.set_value(iter, 2, not model.get_value(iter, 2))
        
    def fill_filelist(self):
        model = self.filelist.get_model()
        for i in range(len(self.changed_editors)):
            editor = self.changed_editors[i]
            if editor.get_filename():
                lbl = os.path.basename(editor.get_filename())
                tip = None
            else:
                lbl = _(u"Unsaved Query %(num)s") % {"num" : i+1}
                content = list()
                lines = editor.get_text().splitlines()
                for line in lines:
                    if len(line) > 35:
                        content.append(line[:35]+"...")
                    else:
                        content.append(line)
                    if len(content) == 7:
                        if len(lines) > 7:
                            content.append("...")
                        break
                tip = "\n".join(content)
            model.append([editor, lbl, True, tip])
        
    def set_dialog_mode(self, mode):
        if mode == MODE_SINGLE:
            self.xml.get_widget("lbl_filelist").hide()
            self.xml.get_widget("sw_filelist").hide()
            self.xml.get_widget("filelist").hide()
            editor = self.changed_editors[0]
            if editor.get_filename():
                filename = os.path.basename(editor.get_filename())
            else:
                filename = _(u"Unsaved Query %(num)s") % {"num" : 1} 
            msg_header = _(u'Save the changes to document "%(filename)s" before closing?') % {"filename":filename}
        else:
            self.xml.get_widget("lbl_filelist").show()
            self.xml.get_widget("sw_filelist").show()
            msg_header = _(u"There are %(num)d documents with unsaved changes. Save changes before closing?")
            msg_header = msg_header % {"num" : len(self.changed_editors)}
        lbl = self.xml.get_widget("lbl_header").get_label()
        self.xml.get_widget("lbl_header").set_markup(lbl % msg_header)
        
    def save_files(self):
        model = self.filelist.get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 2):
                if not model.get_value(iter, 0).save_file(default_name=model.get_value(iter, 1)):
                    return False
            iter = model.iter_next(iter)
        return True