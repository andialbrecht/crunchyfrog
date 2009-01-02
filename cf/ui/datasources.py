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

"""Datasources"""

import gtk
import gobject

from gettext import gettext as _

from cf.ui import GladeWidget, dialogs
from cf.ui.widgets import ConnectionsWidget
from cf.datasources import DatasourceInfo

COMMON_OPTIONS = ["dsn", "database", "host", "port", "user", "password"]

class DatasourceManager(GladeWidget):

    def __init__(self, win):
        self.instance = win
        GladeWidget.__init__(self, win, "glade/datasourcemanager",
                             "datasourcemanager")
        from cf.plugins.core import PLUGIN_TYPE_BACKEND
        if not self.app.plugins.get_plugins(PLUGIN_TYPE_BACKEND, True):
            self.run = self.run_warning
        self.set_data("be_widgets", dict())

    def _setup_widget(self):
        # Fix help button
        btn = self.xml.get_widget("btn_help_ds")
        box = self.xml.get_widget("dialog-action_area8")
        box.set_child_secondary(btn, True)
        # Backends
        cmb = self.xml.get_widget("cmb_backends")
        model = gtk.ListStore(gobject.TYPE_PYOBJECT,
                              str, str)
        model.set_sort_column_id(2, gtk.SORT_ASCENDING)
        cmb.set_model(model)
        cell = gtk.CellRendererText()
        cmb.pack_start(cell, True)
        cmb.add_attribute(cell, "markup", 1)
        self._init_backends(model)
        # Saved connections
        tv = self.xml.get_widget("tv_stored_connections")
        model = gtk.ListStore(gobject.TYPE_PYOBJECT,
                              str)
        model.set_sort_column_id(1, gtk.SORT_ASCENDING)
        tv.set_model(model)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), markup=1)
        tv.append_column(col)
        sel = tv.get_selection()
        sel.connect("changed", self.on_selected_datasource_changed)
        self.refresh_saved_connections()
        # Connections
        notebook = self.xml.get_widget("dsmanager_notebook")
        self.connections = ConnectionsWidget(self.win)
        lbl = gtk.Label(_(u"_Connections"))
        lbl.set_use_underline(True)
        self.connections.widget.set_border_width(5)
        notebook.append_page(self.connections.widget, lbl)

    def run_warning(self):
        dialogs.warning(_(u"No active database backends."),
                        _(u"Open preferences and activate at least one database backend plugin."))

    def _init_backends(self, model):
        model.clear()
        nb = self.xml.get_widget("nb_options")
        from cf.plugins.core import PLUGIN_TYPE_BACKEND
        for be in self.app.plugins.get_plugins(PLUGIN_TYPE_BACKEND, True):
            iter = model.append(None)
            model.set(iter, 0, be, 1, be.name, 2, be.name)
        iter = model.append(None)
        model.set(iter, 0, -1, 1, "<i>%s</i>" % _(u"Other..."), 2, "Z"*10)

    def _on_ask_for_password(self, check):
        return check.get_active()

    def _on_get_data_from_entry(self, entry):
        return entry.get_text().strip() or None

    def _on_get_port(self, spin):
        return spin.get_value_as_int() or None

    def _create_widget_database(self, data_widgets, conn=None):
        e = gtk.Entry()
        if conn and conn.options.get("database", None):
            e.set_text(conn.options.get("database"))
        data_widgets["database"] = (self._on_get_data_from_entry, e)
        return data_widgets, gtk.Label(_(u"Database:")), e

    def _create_widget_dsn(self, data_widgets, conn=None):
        e = gtk.Entry()
        if conn and conn.options.get("dsn", None):
            e.set_text(conn.options.get("dsn"))
        data_widgets["dsn"] = (self._on_get_data_from_entry, e)
        return data_widgets, gtk.Label(_(u"DSN:")), e

    def _create_widget_host(self, data_widgets, conn=None):
        e = gtk.Entry()
        if conn and conn.options.get("host", None):
            e.set_text(conn.options.get("host"))
        data_widgets["host"] = (self._on_get_data_from_entry, e)
        return data_widgets, gtk.Label(_(u"Host:")), e

    def _create_widget_port(self, data_widgets, conn=None):
        s = gtk.SpinButton(climb_rate=1, digits=0)
        s.set_range(0, 999999)
        s.set_increments(1, 10)
        if conn and conn.options.get("port", None):
            s.set_value(conn.options.get("port"))
        #self.app.ui.tt.set_tip(s, _(u"Setting port number to 0 means no port."))
        data_widgets["port"] = (self._on_get_port, s)
        return data_widgets, gtk.Label(_(u"Port:")), s

    def _create_widget_user(self, data_widgets, conn=None):
        e = gtk.Entry()
        if conn and conn.options.get("user", None):
            e.set_text(conn.options.get("user"))
        data_widgets["user"] = (self._on_get_data_from_entry, e)
        return data_widgets, gtk.Label(_(u"User:")), e

    def _create_widget_password(self, data_widgets, conn=None):
        def check_toggled(check, entry):
            entry.set_sensitive(not check.get_active())
        e = gtk.Entry()
        e.set_visibility(False)
        if conn and conn.options.get("password", None):
            e.set_text(conn.options.get("password"))
        data_widgets["password"] = (self._on_get_data_from_entry, e)
        check = gtk.CheckButton(_(u"_Ask for password"))
        check.connect("toggled", check_toggled, e)
        if conn:
            check.set_active(conn.options.get("ask_for_password", False))
        data_widgets["ask_for_password"] = (self._on_ask_for_password, check)
        box = gtk.VBox()
        box.pack_start(e, False)
        box.pack_start(check, False)
        return data_widgets, gtk.Label(_(u"Password:")), box

    def on_be_test_connection(self, btn):
        data = self.get_backend_options()
        lbl = self.xml.get_widget("lbl_testconnection")
        lbl.set_text("")
        combo = self.xml.get_widget("cmb_backends")
        iter = combo.get_active_iter()
        model = combo.get_model()
        be = model.get_value(iter, 0)
        err = be.test_connection(data)
        if err:
            dialogs.error(_(u"Connection failed"), err)
        else:
            lbl.set_text(_(u"Successful."))

    def on_cmb_backends_changed(self, combo):
        self.set_backend_option_widgets()

    def on_delete_datasource(self, *args):
        conn = self.get_selected_saved_connection()
        if not conn: return
        conn.delete()
        self.refresh_saved_connections()

    def on_new_datasource(self, *args):
        sel = self.xml.get_widget("tv_stored_connections").get_selection()
        sel.unselect_all()
        self.clear_fields()

    def on_response(self, dialog, response_id):
        if response_id == 0:
            dialog.stop_emission("response")
            self.instance.show_help("crunchyfrog-datasources")
            return True

    def on_save_datasource(self, *args):
        conn = self.get_connection()
        conn.save()
        self.refresh_saved_connections(conn.db_id)

    def on_selected_datasource_changed(self, *args):
        conn = self.get_selected_saved_connection()
        if conn and not self.app.plugins.is_active(conn.backend):
            dialogs.error(_(u'Plugin not active'),
                          _(u'Please activate the following plugin '
                            'to use this data source: ')+conn.backend.name+'.')
            return
        self.xml.get_widget("btn_delete").set_sensitive(bool(conn))
        self.clear_fields()
        if not conn:
            return
        self.xml.get_widget("entry_name").set_text(conn.name or "")
        self.xml.get_widget("entry_description").set_text(conn.description or "")
        self.select_backend_by_id(conn.backend.id)
        self.set_backend_option_widgets(conn)

    def on_toggle_save_button(self, *args):
        btn = self.xml.get_widget("btn_save")
        cmb = self.xml.get_widget("cmb_backends")
        if self.xml.get_widget("entry_name").get_text().strip() \
        and self.xml.get_widget("cmb_backends").get_active_iter():
            btn.set_sensitive(True)
        else:
            btn.set_sensitive(False)

    def clear_fields(self):
        self.xml.get_widget("entry_name").set_text("")
        self.xml.get_widget("entry_description").set_text("")
        cmb = self.xml.get_widget("cmb_backends")
        cmb.set_active(-1)
        self.xml.get_widget("lbl_testconnection").set_text("")

    def get_backend_options(self):
        data_widgets = self.get_data("be_widgets")
        data = dict()
        for key, value in data_widgets.items():
            data[key] = value[0](value[1])
        return data

    def get_connection(self):
        db_id = None
        conn_info = self.get_selected_saved_connection()
        if conn_info:
            db_id = conn_info.db_id
        conn = DatasourceInfo(self.app, self.get_selected_backend(),
                          self.xml.get_widget("entry_name").get_text().strip() or None,
                          self.xml.get_widget("entry_description").get_text().strip() or None,
                          self.get_backend_options(),
                              db_id)
        return conn

    def get_selected_backend(self):
        combo = self.xml.get_widget("cmb_backends")
        iter = combo.get_active_iter()
        if iter:
            model = combo.get_model()
            return model.get_value(iter, 0)
        else:
            return None

    def get_selected_saved_connection(self):
        sel = self.xml.get_widget("tv_stored_connections").get_selection()
        model, iter = sel.get_selected()
        if iter:
            return model.get_value(iter, 0)
        else:
            return None

    def refresh_saved_connections(self, active=None):
        model = self.xml.get_widget("tv_stored_connections").get_model()
        model.clear()
        for item in DatasourceInfo.load_all(self.app):
            iter = model.append(None)
            lbl = item.get_label()
            if item.description and item.description.strip():
                lbl += '\n<span size="small">'+item.description+'</span>'
            if not self.app.plugins.is_active(item.backend):
                lbl += '\n<span foreground="red">'+_(u'Plugin not active.')+'</span>'
            model.set(iter,
                      0, item,
                      1, lbl)
            if active and item.db_id == active:
                sel = self.xml.get_widget("tv_stored_connections").get_selection()
                sel.select_iter(iter)

    def run_be_info_dialog(self):
        dlg = BackendInfoDialog(self.instance)
        dlg.run()
        dlg.destroy()

    def select_backend_by_id(self, be_id):
        combo = self.xml.get_widget("cmb_backends")
        model = combo.get_model()
        iter = model.get_iter_first()
        while iter:
            be = model.get_value(iter, 0)
            if be.id == be_id:
                combo.set_active_iter(iter)
                return True
            iter = model.iter_next(iter)
        return False

    def set_backend_option_widgets(self, initial_data=None):
        be = self.get_selected_backend()
        if be == -1:
            self.run_be_info_dialog()
            combo = self.xml.get_widget("cmb_backends")
            combo.set_active(-1)
            return
        data_widgets = dict()
        if be:
            data_widgets, widgets = be.get_datasource_options_widgets(data_widgets, initial_data)
        else:
            widgets = []
        vbox = self.xml.get_widget("vbox_be_options")
        while vbox.get_children():
            vbox.remove(vbox.get_children()[0])
        if not widgets:
            vbox.pack_start(gtk.Label(""))
        else:
            for widget in widgets:
                if widget in COMMON_OPTIONS:
                    data_widgets, lbl, x = getattr(self, "_create_widget_%s" % widget)(data_widgets, initial_data)
                    a = gtk.Alignment(0, 0)
                    a.add(lbl)
                    vbox.pack_start(a, False, False)
                    vbox.pack_start(x, False, False)
                else:
                    vbox.pack_start(widget, False, False)
        vbox.show_all()
        self.set_data("be_widgets", data_widgets)
        self.xml.get_widget("btn_test_connection").set_sensitive(bool(be))


class BackendInfoDialog(GladeWidget):

    def __init__(self, instance):
        GladeWidget.__init__(self, instance,
                             "crunchyfrog", "backend_info_dialog")
        self.populate()

    def _setup_widget(self):
        self.list = self.xml.get_widget("list_backends")
        model = gtk.ListStore(str, str)
        self.list.set_model(model)
        col = gtk.TreeViewColumn("", gtk.CellRendererPixbuf(), stock_id=0)
        self.list.append_column(col)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), markup=1)
        self.list.append_column(col)

    def populate(self):
        model = self.list.get_model()
        from cf.plugins.core import PLUGIN_TYPE_BACKEND
        for be in self.app.plugins.get_plugins(PLUGIN_TYPE_BACKEND):
            iter = model.append(None)
            if be.INIT_ERROR:
                ico = "gtk-dialog-error"
                lbl = be.name+"\n"+be.INIT_ERROR
            elif  self.app.plugins.is_active(be):
                ico = "gtk-apply"
                lbl = be.name
            else:
                ico = "gtk-dialog-warning"
                lbl = be.name+"\n"+_(u"Plugin not active")
            model.set(iter, 0, ico, 1, lbl)
