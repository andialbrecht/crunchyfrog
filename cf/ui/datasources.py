# -*- coding: utf-8 -*-

# crunchyfrog - a database schema browser and query tool
# Copyright (C) 2009 Andi Albrecht <albrecht.andi@gmail.com>
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

"""Dialog to manage data sources and connections."""

import sys
from gettext import gettext as _

import gobject
import gtk

import cf.db
from cf.db.backends import GUIOption
from cf.ui import dialogs
from cf.ui.widgets.sqlview import SQLView


class DatasourcesDialog(object):


    def __init__(self, app, parent=None):
        self.app = app
        self.builder = gtk.Builder()
        self.builder.set_translation_domain('crunchyfrog')
        self.builder.add_from_file(app.get_glade_file('datasources.glade'))
        self.builder.connect_signals(self)
        self.dlg = self.builder.get_object('datasources_dialog')
        self.dlg.set_transient_for(parent)
        self.init_datasources()
        self.refresh_datasources()
        self.init_providers()
        self.refresh_providers()
        self._ds_sigs = []
        ds = self.app.datasources
        self._ds_sigs.append(ds.connect('datasource-changed',
                                        lambda *a: self.refresh_datasources()))
        self._ds_sigs.append(ds.connect('datasource-added',
                                        lambda *a: self.refresh_datasources()))
        self._ds_sigs.append(ds.connect('datasource-deleted',
                                        lambda *a: self.refresh_datasources()))

    # -----------------
    # Dialog callbacks
    # -----------------

    def on_close(self, *args):
        self.app.set_data('dialog_datasources', None)
        self.destroy()

    def on_response(self, dialog, response_id):
        if response_id == -1:  # help button
            dialog.stop_emission('response')
            self.app.show_help('datasources')
            return True

    def on_show_help(self, *args):
        self.app.show_help('datasources')
        self.stop_emission('clicked')
        return True

    # -----------
    # Datsources
    # -----------

    def init_datasources(self):
        treeview = self.builder.get_object('list_datasources')
        model = gtk.ListStore(gobject.TYPE_PYOBJECT,  # 0 datasource
                              str,                    # 1 label
                              str,                    # 2 color
                              )
        model.set_sort_column_id(1, gtk.SORT_ASCENDING)
        treeview.set_model(model)
        col = gtk.TreeViewColumn()
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, 'background', 2)
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'markup', 1)
        treeview.append_column(col)
        selection = treeview.get_selection()
        selection.connect('changed', self.on_selected_datasource_changed)
        treeview.connect('row-activated', self.on_row_activated)

    def refresh_datasources(self):
        treeview = self.builder.get_object('list_datasources')
        model = treeview.get_model()
        model.clear()
        for datasource in self.app.datasources.get_all():
            if datasource.name:
                label = ('<b>%s (%s)</b>'
                         % (gobject.markup_escape_text(datasource.name),
                            gobject.markup_escape_text(datasource.public_url)))
            else:
                label = ('<b>%s</b>'
                         % gobject.markup_escape_text(datasource.public_url))
            if datasource.description:
                label += ('\n<span size="small">%s</span>'
                          % gobject.markup_escape_text(datasource.description))
            else:
                label += ('\n<span size="small"><i>%s</i></span>'
                          % _(u'No description available.'))
            model.append([datasource, label, datasource.color])

    def get_selected_datasource(self):
        treeview = self.builder.get_object('list_datasources')
        selection = treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_ is None:
            return None
        return model.get_value(iter_, 0)

    def on_datasource_new(self, *args):
        dlg = DatasourceEditDialog(self.app, self.dlg)
        dlg.run()
        dlg.destroy()

    def on_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        iter_ = model.get_iter(path)
        self.edit_datasource(model.get_value(iter_, 0))

    def on_selected_datasource_changed(self, selection):
        model, iter_ = selection.get_selected()
        for name in ('btn_datasource_edit', 'btn_datasource_delete'):
            widget = self.builder.get_object(name)
            widget.set_sensitive(iter_ is not None)

    def on_edit_datasource(self, *args):
        datasource = self.get_selected_datasource()
        if datasource is None:
            return
        self.edit_datasource(datasource)

    def edit_datasource(self, datasource):
        """Create or edit a data source."""
        dlg = DatasourceEditDialog(self.app, self.dlg, datasource)
        dlg.run()
        dlg.destroy()

    def on_delete_datasource(self, *args):
        datasource = self.get_selected_datasource()
        if datasource is None:
            return
        answer = dialogs.yesno(_(u'Delete Data Source?'), parent=self.dlg)
        if answer == gtk.RESPONSE_YES:
            self.app.datasources.delete(datasource)

    # --------------
    # Provider page
    # --------------

    def _provider_visible(self, model, iter):
        """visible filter function for provider list"""
        combo = self.builder.get_object('combo_provider_filter')
        cmodel = combo.get_model()
        citer = combo.get_active_iter()
        selected = cmodel.get_value(citer, 0)
        available = model.get_value(iter, 4)
        if selected == 0 and not available:  # active
            return False
        elif selected == 1 and available:  # available
            return False
        return True

    def on_provider_filter_changed(self, *args):
        self.refresh_providers()

    def on_refresh_provider(self, *args):
        self.refresh_providers()


    def init_providers(self):
        # List
        treeview = self.builder.get_object('treeview_provider')
        model = gtk.ListStore(str,  # name (= key)
                              str,  # stock icon
                              str,  # label (markup)
                              str,  # human readable name (for sorting)
                              bool, # available
                              )
        model.set_sort_column_id(3, gtk.SORT_ASCENDING)
        filtered_model = model.filter_new()
        filtered_model.set_visible_func(self._provider_visible)
        treeview.set_model(filtered_model)
        col = gtk.TreeViewColumn()
        renderer = gtk.CellRendererPixbuf()
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, 'stock-id', 1)
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'markup', 2)
        treeview.append_column(col)

    def refresh_providers(self):
        available = cf.db.availability()
        model = self.builder.get_object('treeview_provider').get_model()
        model = model.props.child_model
        model.clear()
        for name in cf.db.DIALECTS:
            data = cf.db.DIALECTS[name]
            label = ('<b>%s</b>\n<span size="small">%s</span>'
                     % (gobject.markup_escape_text(data['name']),
                        gobject.markup_escape_text(data['description'])))
            if available[name][0] == True:
                icon = 'gtk-apply'
            else:
                icon = 'gtk-dialog-warning'
                label += (' <span foreground="red" size="small">(%s)</span>'
                          % gobject.markup_escape_text(available[name][1]))
            model.append([name, icon, label, data['name'],
                          available[name][0]])

    def destroy(self):
        while self._ds_sigs:
            self.app.datasources.disconnect(self._ds_sigs.pop())
        self.dlg.destroy()

    def run(self):
        return self.dlg.run()


class DatasourceEditDialog(object):

    def __init__(self, app, parent=None, datasource=None):
        self.app = app
        self.builder = gtk.Builder()
        self.builder.set_translation_domain('crunchyfrog')
        self.builder.add_from_file(app.get_glade_file('datasourceedit.glade'))
        self.builder.connect_signals(self)
        self.dlg = self.builder.get_object('dialog_datasource_edit')
        self.dlg.set_transient_for(parent)
        self.datasource = None
        self.widget_startup_commands = None
        self.populate_dbtype()
        self.setup_startup_commands()
        if datasource:
            self.set_datasource(datasource)

    def run(self):
        return self.dlg.run()

    def destroy(self):
        self.dlg.destroy()

    def on_response(self, dlg, response_id):
        if response_id == 1:  # test connection
            dlg.stop_emission('response')
            self.test_connection()
            return True
        elif response_id == 2:  # ok button
            res = self.save_datasource()
            if not res:
                dlg.stop_emission('response')
                return True

    def populate_dbtype(self):
        model = self.builder.get_object('model_dbtype')
        model.clear()
        model.set_sort_column_id(1, gtk.SORT_ASCENDING)
        available = [key for key, value in cf.db.availability().iteritems()
                     if value[0] == True]
        for key in cf.db.DIALECTS:
            if key not in available:
                continue
            model.append([key, cf.db.DIALECTS[key]['name']])

    def setup_startup_commands(self):
        sw = self.builder.get_object('sw_startup_commands')
        editor = SQLView(self)
        editor.set_show_line_numbers(False)
        sw.add(editor)
        editor.show()
        self.widget_startup_commands = editor

    def set_datasource(self, datasource):
        combo = self.builder.get_object('combo_dbtype')
        model = combo.get_model()
        iter_ = model.get_iter_first()
        while iter_:
            if model.get_value(iter_, 0) == datasource.url.drivername:
                combo.set_active_iter(iter_)
                break
            iter_ = model.iter_next(iter_)
        self.builder.get_object('entry_name').set_text(datasource.name or '')
        entry = self.builder.get_object('entry_description')
        entry.set_text(datasource.description or '')
        backend = self.get_selected_backend()
        backend_options = {}
        [backend_options.setdefault(option.key, option)
         for option in backend.get_options()]
        data = datasource.to_dict()
        for child in self.builder.get_object('table_connection_settings'):
            key = child.get_data('cf::key')
            if key is None:
                continue
            if key in data and key in backend_options:
                option = backend_options[key]
                if option.widget == option.WIDGET_CHECKBOX:
                    child.set_active(data[key])
                elif option.widget == option.WIDGET_FILECHOOSER:
                    child.set_filename(data[key])
                elif option.widget == option.WIDGET_COMBO:
                    model = child.get_model()
                    iter_ = model.get_iter_first()
                    while iter_:
                        if model.get_value(iter_, 0) == data[key]:
                            child.set_active_iter(iter_)
                            break
                        iter_ = model.iter_next(iter_)
                else:
                    if data[key] is None:
                        val = ''
                    else:
                        val = str(data[key])
                    child.set_text(val)
            elif key == 'ask_for_password':
                child.set_active(data['ask_for_password'])
        buffer_ = self.widget_startup_commands.get_buffer()
        buffer_.set_text(datasource.startup_commands or '')
        check = self.builder.get_object('check_color')
        check.set_active(datasource.color is not None)
        if datasource.color is not None:
            btn = self.builder.get_object('colorbutton_datasource')
            btn.set_color(gtk.gdk.color_parse(datasource.color))
        self.datasource = datasource

    def get_selected_backend(self):
        """Returns the selected backend or ``None``."""
        combo = self.builder.get_object('combo_dbtype')
        model = combo.get_model()
        iter_ = combo.get_active_iter()
        if iter_ is None:
            return None
        return cf.db.get_dialect_backend(model.get_value(iter_, 0))

    def on_check_color_toggled(self, check):
        btn = self.builder.get_object('colorbutton_datasource')
        btn.set_sensitive(check.get_active())

    def on_dbtype_changed(self, combo):
        backend = self.get_selected_backend()
        for item in ['lbl_name', 'entry_name',
                     'lbl_description', 'entry_description',
                     'lbl_color', 'check_color',
                     'frame_connection', 'btn_test_connection']:
            self.builder.get_object(item).set_sensitive(backend is not None)
        table = self.builder.get_object('table_connection_settings')
        table.foreach(lambda child: table.remove(child))
        if backend is None:
            return
        row = 0
        for option in backend.get_options():
            row += 1
            second_widget = None
            table.resize(row, 2)
            lbl = gtk.Label('%s:' % option.label)
            lbl.set_alignment(0, 0.5)
            if option.widget == option.WIDGET_CHECKBOX:
                entry = gtk.CheckButton()
            elif option.widget == option.WIDGET_PASSWORD:
                entry = gtk.Entry()
                entry.set_visibility(False)
                second_widget = gtk.CheckButton(_(u'Ask for password'))
                cb = lambda chk, e: e.set_sensitive(not chk.get_active())
                second_widget.connect('toggled', cb, entry)
                second_widget.set_data('cf::key', 'ask_for_password')
            elif option.widget == option.WIDGET_FILECHOOSER:
                entry = gtk.FileChooserButton(_(u'Select file'))
            elif option.widget == option.WIDGET_COMBO:
                model = gtk.ListStore(gobject.TYPE_PYOBJECT, str)
                entry = gtk.ComboBox(model)
                cell = gtk.CellRendererText()
                entry.pack_start(cell, True)
                entry.add_attribute(cell, 'text', 1)
                for choice in option.choices:
                    model.append(choice)
            # TODO: Port widget
            else:
                entry = gtk.Entry()
            if option.tooltip is not None:
                entry.set_tooltip_text(option.tooltip)
            entry.set_data('cf::key', option.key)
            if option.key == 'url':
                entry.set_text('%s://' % backend.drivername)
                entry.set_tooltip_text(_(u'An URL'))

            table.attach(lbl, 0, 1, row-1, row,
                         xoptions=gtk.FILL,
                         yoptions=gtk.FILL)
            table.attach(entry, 1, 2, row-1, row,
                         yoptions=gtk.FILL)
            if second_widget:
                row += 1
                table.attach(second_widget, 1, 2, row-1, row,
                             yoptions=gtk.FILL)
        table.show_all()

    def _get_value_from_widget(self, option):
        """Retrieves the value for an backend option from widget."""
        table = self.builder.get_object('table_connection_settings')
        for child in table.get_children():
            key = child.get_data('cf::key')
            if key != option.key:
                continue
            if option.widget == option.WIDGET_CHECKBOX:
                return child.get_active()
            elif option.widget == option.WIDGET_FILECHOOSER:
                return child.get_filename()
            elif option.widget == option.WIDGET_COMBO:
                model = child.get_model()
                iter_ = child.get_active_iter()
                if iter_ is None:
                    return None
                return model.get_value(iter_, 0)
            else:
                return child.get_text().strip() or None
        return None

    def _get_url_options(self):
        """Collects URL related options."""
        backend = self.get_selected_backend()
        options = {}
        for option in backend.get_options():
            value = self._get_value_from_widget(option)
            options[option.key] = value
            if option.key == 'password':
                opt = GUIOption('ask_for_password', '',
                                widget=GUIOption.WIDGET_CHECKBOX)
                opt.key = 'ask_for_password'
                options['ask_for_password'] = self._get_value_from_widget(opt)
        return options

    def get_sa_url(self):
        """Create and return SQLAlchemy URL from widgets."""
        options = self._get_url_options()
        backend = self.get_selected_backend()
        return backend.create_url(options)

    def make_datasource(self, create_new=False):
        """Apply current settings to data source or create a new one."""
        if self.datasource and not create_new:
            ds = self.datasource
        else:
            ds = cf.db.Datasource(self.app.datasources)
        ds.url = self.get_sa_url()
        data = self._get_url_options()
        if 'ask_for_password' in data:
            ds.ask_for_password = data['ask_for_password']
        ds.name = self.builder.get_object('entry_name').get_text() or None
        widget = self.builder.get_object('entry_description')
        ds.description = widget.get_text() or None
        if self.builder.get_object('check_color').get_active():
            btn = self.builder.get_object('colorbutton_datasource')
            ds.color = btn.get_color().to_string()
        else:
            ds.color = None
        buffer_ = self.widget_startup_commands.get_buffer()
        ds.startup_commands = buffer_.get_text(*buffer_.get_bounds()) or None
        return ds

    def clean_data(self):
        """Validates the form data."""
        data = self._get_url_options()
        backend = self.get_selected_backend()
        required = []
        errors = []
        for option in backend.get_options():
            value = data.get(option.key, None)
            if option.required and value is None:
                required.append(option)
            elif value and option.widget == option.WIDGET_PORT:
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append((option, _(u'Integer required')))
        return {'required': required, 'errors': errors}

    def validate_data(self):
        """Validates data and displays dialog on errors."""
        result = self.clean_data()
        msg = ''
        if result['required']:
            msg += _(u'Missing fields:\n%(fields)s')
            msg += msg % {'fields': ', '.join(
                [opt.label for opt in result['required']])}
        if result['errors']:
            msg += _(u'Validation errors:\n')
            msg += '\n'.join('%s: %s' % (opt.label, err)
                             for opt, err in result['errors'])
        if msg:
            dialogs.error(_(u'Failed'), msg, parent=self.dlg)
            return False
        return True

    def test_connection(self):
        """Test the current settings."""
        if not self.validate_data():
            return
        ds = self.make_datasource(create_new=True)
        try:
            conn = ds._open_connection()
            conn.close()
            dialogs.info(_(u'Succeeded'), parent=self.dlg)
        except:
            import logging
            logging.exception('Test connect failed. Traceback follows:')
            dialogs.error(_(u'Failed'), str(sys.exc_info()[1]))

    def save_datasource(self):
        """Save current settings."""
        if not self.validate_data():
            return False
        ds = self.make_datasource()
        self.app.datasources.save(ds)
        return True
