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

"""Instance selector class"""

import os.path

import gtk

import cf


class InstanceSelector(object):

    def __init__(self, client):
        self.client = client
        self.builder = gtk.Builder()
        self.builder.set_translation_domain('crunchyfrog')
        fname = os.path.join(cf.DATA_DIR, 'glade/instanceselector.glade')
        self.builder.add_from_file(fname)
        self.builder.connect_signals(self)
        self.dlg = self.builder.get_object('instanceselector')
        self._setup_widget()
        self._setup_connections()

    def _setup_widget(self):
        model = gtk.ListStore(int, str)
        self.list = self.builder.get_object("list_instances")
        self.list.set_model(model)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=1)
        self.list.append_column(col)
        for id, title in self.client.get_instances():
            model.append([id, title])

    def _setup_connections(self):
        sel = self.list.get_selection()
        sel.connect("changed", self.on_isel_changed)
        self.builder.get_object("btn_newinstance").connect(
            "toggled", self.on_newi_toggled)

    # ---------
    # Callbacks
    # ---------

    def on_newi_toggled(self, btn):
        sel = self.list.get_selection()
        model = self.list.get_model()
        if btn.get_active():
            sel.unselect_all()
        else:
            sel.select_iter(model.get_iter_first())
        self.list.set_sensitive(not btn.get_active())

    def on_isel_changed(self, selection):
        model, iter = selection.get_selected()
        if not iter:
            self.builder.get_object("btn_newinstance").set_active(True)
        else:
            self.builder.get_object("btn_activeinstance").set_active(True)

    # --------------
    # Public methods
    # --------------

    def run(self):
        """Run the dialog."""
        return self.dlg.run()

    def destroy(self):
        """Destroy the dialog."""
        return self.dlg.destroy()

    def get_instance_id(self):
        if self.builder.get_object("btn_newinstance").get_active():
            return None
        else:
            sel = self.list.get_selection()
            model, iter = sel.get_selected()
            if iter:
                return model.get_value(iter, 0)
            return None
