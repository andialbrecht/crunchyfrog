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

"""Custom statusbar"""

import gtk

from cf.ui.editor import Editor


class CrunchyStatusbar(gtk.Statusbar):
    """An extended gtk.Statusbar."""

    def __init__(self, app, instance):
        """Constructor."""
        gtk.Statusbar.__init__(self)
        self.app = app
        self.instance = instance
        self._editor_sigs = {'connection-changed': None,
                             'toggle-overwrite': None,
                             'insert-mark': None}
        self._editor = None

        self.lbl_conn = gtk.Label()
        self.lbl_conn.set_alignment(0, 0.5)
        self.lbl_conn.show()
        self._add_item(self.lbl_conn, False, True)
        self.lbl_curpos = gtk.Label()
        self.lbl_curpos.set_alignment(1, 0.5)
        self.lbl_curpos.set_width_chars(15)
        self.lbl_curpos.show()
        self._add_item(self.lbl_curpos, False, True)
        self.lbl_insmode = gtk.Label()
        self.lbl_insmode.set_width_chars(4)
        self.lbl_insmode.show()
        self._add_item(self.lbl_insmode, False, True)

        self.instance.connect('active-editor-changed',
                              lambda i, e: self.set_editor(e))

    def _add_item(self, widget, expand=True, fill=True, padding=0):
        """Adds a widget to the statusbar using pack_start.

        Returns:
          The gtk.Frame holding the widget.
        """
        frame = gtk.Frame()
        frame.set_border_width(0)
        shadow_type = self.style_get_property('shadow_type')
        frame.set_property('shadow_type', shadow_type)
        frame.add(widget)
        frame.show()
        self.pack_start(frame, expand, fill, padding)
        return frame

    def _disconnect_editor_sigs(self):
        """Disconnects editor signals, if any."""
        if self._editor is not None:
            sigs = self._editor_sigs
            if sigs['connection-changed'] is not None:
                self._editor.disconnect(sigs['connection-changed'])
            if sigs['toggle-overwrite'] is not None:
                self._editor.textview.disconnect(sigs['toggle-overwrite'])
            if sigs['insert-mark'] is not None:
                self._editor.textview.buffer.disconnect(sigs['insert-mark'])
        self._editor_sigs['connection-changed'] = None
        self._editor_sigs['toggle-overwrite'] = None
        self._editor_sigs['insert-mark'] = None

    def _connect_editor_sigs(self):
        """Connect to some editor signals to track changes."""
        if self._editor is None or not isinstance(self._editor, Editor):
            return
        sig = self._editor.connect(
            'connection-changed',
            lambda e, c: self._set_connection_label(e))
        self._editor_sigs['connections-changed'] = sig
        sig = self._editor.textview.connect(
            'toggle-overwrite',
            lambda tv: self._set_overwrite_mode(self._editor, False))
        self._editor_sigs['toggle.overwrite'] = sig
        sig = self._editor.textview.buffer.connect('mark-set',
                                                   self.on_tv_mark_set)

    def _set_connection_label(self, editor):
        if editor is None:
            lbl = ''
        else:
            if editor.connection is not None:
                lbl = editor.connection.get_label()
            else:
                lbl = _(u'[Not connected]')
        self.lbl_conn.set_text(lbl)

    def _set_curpos(self, line=None, offset=None):
        if line is None or offset is None:
            lbl = ''
        else:
            lbl = _(u'Ln %(line)d, Col %(column)d') % {'line': line,
                                                       'column': offset}
        self.lbl_curpos.set_text(lbl)

    def _set_overwrite_mode(self, editor, toggle_bool=True):
        if editor is None:
            lbl = ''
        elif isinstance(editor, Editor):
            overwrite = editor.textview.get_overwrite()
            if toggle_bool:
                overwrite = not overwrite
            lbl = overwrite and _(u'INS') or _(u'OVR')
        else:
            lbl = ''
        self.lbl_insmode.set_text(lbl)

    # ---
    # Callbacks
    # ---

    def on_tv_mark_set(self, textbuffer, iter_, mark):
        mark = textbuffer.get_insert()
        iter_ = textbuffer.get_iter_at_mark(mark)
        self._set_curpos(iter_.get_line()+1, iter_.get_line_offset()+1)

    # ---
    # Public methods
    # ---

    def set_editor(self, editor):
        """Associates an editor with the statusbar.

        This method is (loosely) connected to the instance's
        'active-editor-changed' signal.

        Arguments:
          editor: Editor instance or None.
        """
        self._disconnect_editor_sigs()
        self.instance.statusbar.pop(1)
        self._editor = editor
        self._set_connection_label(self._editor)
        self._set_overwrite_mode(self._editor)
        if self._editor is None:
            self._set_curpos(None, None)
        elif isinstance(self._editor, Editor):
            self.on_tv_mark_set(self._editor.textview.buffer, None, None)
        if self._editor is None:
            return
        self._connect_editor_sigs()

    def set_message(self, msg):
        """Show an informal message in the statusbar.

        This method is just a wrapper for gtk.Statusbar.push(0, msg).

        Args:
          msg: Informal message (str).
        """
        self.push(0, msg)
