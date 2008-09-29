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

"""Custom toolbar"""

import gtk
import gobject

from gettext import gettext as _

from cf.backends import TRANSACTION_IDLE, TRANSACTION_COMMIT_ENABLED, TRANSACTION_ROLLBACK_ENABLED
from cf.ui import GladeWidget
from cf.ui.widgets import ConnectionButton

class CFToolbar(GladeWidget):

    def __init__(self, app, xml, cb_provider=None):
        GladeWidget.__init__(self, app, xml, "toolbar", cb_provider=cb_provider)
        item = self.xml.get_widget("tb_connection")
        self.tb_connection = ConnectionButton(self.app)
        item.add(self.tb_connection)
        self._editor = None
        self.__editor_signals = list()
        self.__buffer_signals = list()
        self.__conn_signals = list()
        self.set_editor(None)

    def on_buffer_changed(self, buffer, editor):
        btn_save = self.xml.get_widget("tb_save")
        btn_saveas = self.xml.get_widget("tb_saveas")
        if not editor or not editor.get_filename():
            btn_save.set_sensitive(False)
            btn_saveas.set_sensitive(bool(editor))
            return
        btn_save.set_sensitive(editor.file_contents_changed())
        btn_saveas.set_sensitive(True)


    def on_connection_notify(self, connection, property):
        if property.name == "transaction-state":
            value = connection.get_property(property.name)
            gobject.idle_add(self.set_transaction_state, value)

    def on_editor_connection_changed(self, editor, conn):
        if editor != self._editor: return
        self.xml.get_widget("tb_execute").set_sensitive(bool(conn))
        if conn:
            self.set_transaction_state(conn.get_property("transaction-state"))
            self.__conn_signals.append(conn.connect("notify", self.on_connection_notify))
        else:
            self.set_transaction_state(None)
        self.tb_connection.set_editor(editor)

    def set_transaction_state(self, value):
        if value == None:
            for item in ("tb_commit", "tb_rollback", "tb_begin"):
                self.xml.get_widget(item).set_sensitive(False)
                return
        self.xml.get_widget("tb_commit").set_sensitive((value & TRANSACTION_COMMIT_ENABLED) != 0)
        self.xml.get_widget("tb_rollback").set_sensitive((value & TRANSACTION_ROLLBACK_ENABLED) != 0)
        self.xml.get_widget("tb_begin").set_sensitive((value & TRANSACTION_IDLE) != 0)

    def set_editor(self, editor):
        while self.__editor_signals:
            self._editor.disconnect(self.__editor_signals.pop())
        if self._editor:
            buffer = self._editor.get_buffer()
            while self.__buffer_signals:
                buffer.disconnect(self.__buffer_signals.pop())
        self._editor = editor
        self.tb_connection.set_editor(editor)
        for item in ["tb_cut", "tb_copy", "tb_paste"]:
            self.xml.get_widget(item).set_sensitive(bool(editor))
        if self._editor:
            self.__editor_signals.append(self._editor.connect("connection-changed", self.on_editor_connection_changed))
            self.on_editor_connection_changed(self._editor, self._editor.connection)
            buffer = self._editor.get_buffer()
            self.__buffer_signals.append(buffer.connect("changed", self.on_buffer_changed, editor))
