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

"""Preferences"""

from inspect import isclass
from xml.etree import ElementTree as etree

import gtk
import gobject

try:
    import gconf
    HAVE_GCONF = True
except ImportError:
    HAVE_GCONF = False

import os
import sys

from gettext import gettext as _

import logging
log = logging.getLogger("PREFS")



import cf
from cf.ui import GladeWidget, dialogs
from cf.ui.widgets import ProgressDialog
from cf.plugins.core import GenericPlugin

class PreferencesDialog(GladeWidget):

    def __init__(self, win, mode="editor"):
        GladeWidget.__init__(self, win, "preferences", "preferences_dialog")
        self.refresh()
        if mode == "editor":
            curr_page = 1
        elif mode == "plugins":
            curr_page = 2
        else:
            curr_page = 0
        self.xml.get_widget("notebook1").set_current_page(curr_page)

    def _setup_widget(self):
        self._setup_plugins()
        self._setup_editor()
        self._setup_shortcuts()
        # Fix secondary button
        btn = self.xml.get_widget("btn_help")
        box = self.xml.get_widget("dialog-action_area1")
        box.set_child_secondary(btn, True)

    def _setup_editor(self):
        model = gtk.ListStore(int, str, gtk.gdk.Pixbuf)
        iconview = self.xml.get_widget("editor_iconview")
        iconview.set_model(model)
        iconview.set_text_column(1)
        iconview.set_pixbuf_column(2)
        def get_pb(stock):
            return self.app.load_icon(stock, 36, gtk.ICON_LOOKUP_FORCE_SVG)
        model.append([0, _(u"General"), get_pb("gtk-execute")])
        model.append([1, _(u"View"), get_pb("gtk-justify-left")])
        model.append([2, _(u"Editor"), get_pb("gtk-edit")])
        model.append([3, _(u"Fonts & Colors"), get_pb("gtk-font")])
        model.append([4, _(u'Keyboard\nShortcuts'),
                      get_pb('preferences-desktop-keyboard-shortcuts')])
        iconview.connect("selection-changed", self.on_editor_selection_changed)
        schemes = self.xml.get_widget("editor_schemes")
        model = gtk.ListStore(str, str)
        model.set_sort_column_id(1, gtk.SORT_ASCENDING)
        schemes.set_model(model)
        col = gtk.TreeViewColumn("", gtk.CellRendererText(), markup=1)
        schemes.append_column(col)
        import gtksourceview2
        sm = gtksourceview2.style_scheme_manager_get_default()
        selected = None
        for id in sm.get_scheme_ids():
            scheme = sm.get_scheme(id)
            lbl = "<b>%s</b>" % scheme.get_name()
            if scheme.get_description():
                lbl += "\n"+scheme.get_description()
            iter = model.append(None)
            model.set(iter, 0, id, 1, lbl)
            if id == self.app.config.get("editor.scheme"):
                selected = iter
        sel = schemes.get_selection()
        sel.select_iter(selected)
        sel.connect("changed", self.on_editor_option_changed)
        sel.set_data("config_option", "editor.scheme")


    def _setup_plugins(self):
        """Set up the plugins view"""
        self.plugin_model = gtk.TreeStore(gobject.TYPE_PYOBJECT, # 0 Plugin class
                                          bool, # 1 active
                                          str, # 2 label
                                          gtk.gdk.Pixbuf, # 3 icon
                                          bool, # 4 active visible
                                          )
        self.plugin_model.set_sort_column_id(2, gtk.SORT_ASCENDING)
        self.plugin_list = self.xml.get_widget("plugin_list")
        self.plugin_list.set_model(self.plugin_model)
        # label
        col = gtk.TreeViewColumn()
        renderer = gtk.CellRendererToggle()
        renderer.connect("toggled", self.on_plugin_active_toggled)
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, "active", 1)
        col.add_attribute(renderer, "visible", 4)
        renderer = gtk.CellRendererPixbuf()
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, 'pixbuf', 3)
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'markup', 2)
        self.plugin_list.append_column(col)
        sel = self.plugin_list.get_selection()
        sel.connect("changed", self.on_plugin_selection_changed)

    def _setup_shortcuts(self):
        self.shortcuts_model = gtk.TreeStore(str,                  # 0 label
                                             int,                  # 1 keyval
                                             gtk.gdk.ModifierType, # 2 mods
                                             bool,                 # 3 visible
                                             str,                  # 4 tooltip
                                             gobject.TYPE_PYOBJECT,# 5 action
                                             )
        self.list_shortcuts = self.xml.get_widget('list_shortcuts')
        col = gtk.TreeViewColumn(_('Action'), gtk.CellRendererText(), text=0)
        self.list_shortcuts.append_column(col)
        renderer = gtk.CellRendererAccel()
        renderer.connect('accel-edited', self.on_accel_edited)
        col = gtk.TreeViewColumn(_(u'Shortcut'), renderer,
                                 accel_key=1, accel_mods=2, visible=3,
                                 editable=3)
        self.list_shortcuts.append_column(col)
        self.shortcuts_model.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.list_shortcuts.set_model(self.shortcuts_model)

    def _setup_connections(self):
        self.app.plugins.connect("plugin-added", self.on_plugin_added)
        self.app.plugins.connect("plugin-removed", self.on_plugin_removed)

    def on_accel_edited(self, renderer, path, accel_key, accel_mods,
                        hardware_keycode):
        model = self.shortcuts_model
        iter_ = model.get_iter(path)
        action = model.get_value(iter_, 5)
        if not action:
            return
        if accel_key == gtk.keysyms.Delete and not accel_mods:
            accel_key = accel_mods = 0
        model.set_value(iter_, 1, accel_key)
        model.set_value(iter_, 2, accel_mods)
        gtk.accel_map_change_entry(action.get_accel_path(),
                                   accel_key, accel_mods, True)

    def on_editor_reuse_conn_toggled(self, toggle):
        self.app.config.set("editor.reuse_connection", toggle.get_active())

    def on_editor_option_changed(self, widget, *args):
        option = widget.get_data("config_option")
        conf = self.app.config
        if isinstance(widget, gtk.CheckButton):
            conf.set(option, widget.get_active())
        elif isinstance(widget, gtk.SpinButton):
            conf.set(option, widget.get_value_as_int())
        elif isinstance(widget, gtk.FontButton):
            conf.set(option, widget.get_font_name())
        elif isinstance(widget, gtk.TreeSelection):
            model, iter = widget.get_selected()
            conf.set(option, model.get_value(iter, 0))
        if option == "editor.wrap_text":
            self.xml.get_widget("editor_wrap_split").set_sensitive(widget.get_active())
        if option == "editor.right_margin":
            self.xml.get_widget("editor_right_margin_position_box").set_sensitive(widget.get_active())
        if option == "editor.default_font":
            self.xml.get_widget("editor_font_box").set_sensitive(not widget.get_active())
        if option == "plugins.repo_enabled":
            gobject.idle_add(self.refresh_plugins)

    def on_editor_selection_changed(self, iconview):
        model = iconview.get_model()
        for path in iconview.get_selected_items():
            iter = model.get_iter(path)
            nb = self.xml.get_widget("editor_notebook")
            nb.set_current_page(model.get_value(iter, 0))

    def on_help(self, *args):
        self.app.show_help()

    def on_plugin_active_toggled(self, renderer, path):
        iter = self.plugin_model.get_iter(path)
        plugin = self.plugin_model.get_value(iter, 0)
        if isinstance(plugin, etree._Element):
            print plugin
        elif issubclass(plugin, GenericPlugin):
            self.plugin_model.set_value(iter, 1, not renderer.get_active())
            gobject.idle_add(self.app.plugins.set_active, plugin, not renderer.get_active())

    def on_plugin_added(self, manager, plugin):
        iter = self.plugin_model.get_iter_first()
        while iter:
            if self.plugin_model.get_value(iter, 0) == plugin.plugin_type:
                break
            iter = self.plugin_model.iter_next(iter)
        if iter:
            lbl = '<b>%s</b>' % plugin.name or _(u"Unknown")
            if plugin.description:
                lbl += "\n"+plugin.description
            if plugin.icon:
                ico = self.app.load_icon(plugin.icon,
                                         gtk.ICON_SIZE_LARGE_TOOLBAR,
                                         gtk.ICON_LOOKUP_FORCE_SVG)
            else:
                ico = None
            citer = self.plugin_model.append(iter)
            self.plugin_model.set(citer,
                      0, plugin,
                      1, self.app.plugins.is_active(plugin),
                      2, lbl,
                      3, ico,
                      4, True)
        self.refresh_plugins_repo()

    def on_plugin_install(self, *args):
        dlg = gtk.FileChooserDialog(_(u"Install plugin"), None,
                                    gtk.FILE_CHOOSER_ACTION_OPEN,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                     gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        filter = gtk.FileFilter()
        filter.set_name(_(u"CrunchyFrog plugins (*.zip, *.py)"))
        filter.add_pattern("*.zip")
        filter.add_pattern("*.py")
        dlg.add_filter(filter)
        dlg.set_filter(filter)
        if dlg.run() == gtk.RESPONSE_OK:
            uri = dlg.get_uri()
        else:
            uri = None
        dlg.destroy()
        gobject.idle_add(self.app.plugins.install_plugin, uri)

    def on_plugin_removed(self, manager, plugin):
        iter = self.plugin_model.get_iter_first()
        while iter:
            if self.plugin_model.get_value(iter, 0) == plugin.plugin_type:
                citer = self.plugin_model.iter_children(iter)
                while citer:
                    if self.plugin_model.get_value(citer, 0) == plugin:
                        self.plugin_model.remove(citer)
                        self.refresh_plugins_repo()
                        return
                    citer = self.plugin_model.iter_next(citer)
            iter = self.plugin_model.iter_next(iter)

    def on_plugin_prefs_show(self, *args):
        sel = self.plugin_list.get_selection()
        model, iter = sel.get_selected()
        if not iter: return
        obj = model.get_value(iter, 0)
        if not isclass(obj) or not issubclass(obj, GenericPlugin):
            return
        if not obj.has_custom_options:
            return
        obj.run_custom_options_dialog(self.app)

    def on_plugin_show_about(self, *args):
        sel = self.plugin_list.get_selection()
        model, iter = sel.get_selected()
        if not iter: return
        obj = model.get_value(iter, 0)
        if not isclass(obj) or not issubclass(obj, GenericPlugin):
            return
        dlg = gtk.AboutDialog()
        if obj.name: dlg.set_name(obj.name)
        if obj.description: dlg.set_comments(obj.description)
        if obj.icon: dlg.set_logo_icon_name(obj.icon)
        if obj.author: dlg.set_authors([obj.author])
        if obj.license: dlg.set_license(obj.license)
        if obj.homepage: dlg.set_website(obj.homepage)
        if obj.version: dlg.set_version(obj.version)
        dlg.run()
        dlg.destroy()

    def on_plugin_selection_changed(self, selection, *args):
        model, iter = selection.get_selected()
        if not iter:
            return
        obj = model.get_value(iter, 0)
        if isclass(obj) and issubclass(obj, GenericPlugin):
            self.xml.get_widget("plugin_about").set_sensitive(True)
            self.xml.get_widget("plugin_prefs").set_sensitive(obj.has_custom_options)
        else:
            self.xml.get_widget("plugin_about").set_sensitive(False)
            self.xml.get_widget("plugin_prefs").set_sensitive(False)

    def on_plugin_sync_repo(self, *args):
        self.sync_repo_file()

    def on_plugin_folder_show(self, *args):
        gtk.show_uri(self.widget.get_screen(),
                     cf.USER_PLUGIN_URI,
                     gtk.gdk.x11_get_server_time(self.widget.window))

    def refresh(self):
        self.refresh_editor()
        self.refresh_plugins()
        self.refresh_shortcuts()

    def refresh_editor(self):
        config = self.app.config
        gw = self.xml.get_widget
        gw('editor_reuse_connection').set_data('config_option',
                                               'editor.reuse_connection')
        gw("editor_reuse_connection").set_active(
            config.get("editor.reuse_connection"))
        gw("editor_replace_variables").set_data("config_option", "editor.replace_variables")
        gw("editor_replace_variables").set_active(config.get("editor.replace_variables"))
        gw("sqlparse_enabled").set_data("config_option", "sqlparse.enabled")
        gw("sqlparse_enabled").set_active(config.get("sqlparse.enabled"))
        gw("editor_wrap_text").set_data("config_option", "editor.wrap_text")
        gw("editor_wrap_text").set_active(config.get("editor.wrap_text"))
        gw("editor_wrap_split").set_data("config_option", "editor.wrap_split")
        gw("editor_wrap_split").set_active(config.get("editor.wrap_split"))
        gw("editor_wrap_split").set_sensitive(gw("editor_wrap_text").get_active())
        gw("editor_display_line_numbers").set_data("config_option", "editor.display_line_numbers")
        gw("editor_display_line_numbers").set_active(config.get("editor.display_line_numbers"))
        gw("editor_highlight_current_line").set_data("config_option", "editor.highlight_current_line")
        gw("editor_highlight_current_line").set_active(config.get("editor.highlight_current_line"))
        gw("editor_right_margin").set_data("config_option", "editor.right_margin")
        gw("editor_right_margin").set_active(config.get("editor.right_margin"))
        gw("editor_right_margin_position").set_data("config_option", "editor.right_margin_position")
        gw("editor_right_margin_position").set_value(config.get("editor.right_margin_position"))
        gw("editor_right_margin_position_box").set_sensitive(config.get("editor.right_margin"))
        gw("editor_bracket_matching").set_data("config_option", "editor.bracket_matching")
        gw("editor_bracket_matching").set_active(config.get("editor.bracket_matching"))
        gw("editor_tabs_width").set_data("config_option", "editor.tabs_width")
        gw("editor_tabs_width").set_value(config.get("editor.tabs_width"))
        gw("editor_insert_spaces").set_data("config_option", "editor.insert_spaces")
        gw("editor_insert_spaces").set_active(config.get("editor.insert_spaces"))
        gw("editor_auto_indent").set_data("config_option", "editor.auto_indent")
        gw("editor_auto_indent").set_active(config.get("editor.auto_indent"))
        gw("editor_default_font").set_data("config_option", "editor.default_font")
        gw("editor_default_font").set_active(config.get("editor.default_font"))
        if HAVE_GCONF:
            client = gconf.client_get_default()
            default_font = client.get_string("/desktop/gnome/interface/monospace_font_name")
        else:
            default_font = 'Monospace 10'
        gw("editor_default_font").set_label(gw("editor_default_font").get_label() % default_font)
        gw("editor_font_box").set_sensitive(not config.get("editor.default_font"))
        gw("editor_font").set_data("config_option", "editor.font")
        gw("editor_font").set_font_name(config.get("editor.font"))

    def refresh_plugins(self):
        # Repo
        self.xml.get_widget("plugin_enable_repo").set_data("config_option", "plugins.repo_enabled")
        self.xml.get_widget("plugin_enable_repo").set_active(self.app.config.get("plugins.repo_enabled"))
        # Plugins
        model = self.plugin_model
        model.clear()
        for key, value in self.app.plugins.plugin_types.items():
            iter = model.append(None)
            model.set(iter,
                      0, key,
                      1, False,
                      2, '<b>%s</b>' % value[0],
                      3, None,
                      4, False)
            for plugin in self.app.plugins.get_plugins(key):
                lbl = '<b>%s</b>' % plugin.name or _(u"Unknown")
                if plugin.description:
                    lbl += "\n"+plugin.description
                if plugin.INIT_ERROR:
                    lbl += '\n<span color="red">'
                    lbl += _(u'ERROR')+': '+plugin.INIT_ERROR+'</span>'
                if plugin.icon:
                    ico = self.app.load_icon(plugin.icon,
                                             gtk.ICON_SIZE_LARGE_TOOLBAR,
                                             gtk.ICON_LOOKUP_FORCE_SVG)
                else:
                    ico = None
                citer = model.append(iter)
                model.set(citer,
                          0, plugin,
                          1, self.app.plugins.is_active(plugin),
                          2, lbl,
                          3, ico,
                          4, not bool(plugin.INIT_ERROR))
        gobject.idle_add(self.refresh_plugins_repo)

    def _plugin_iter_for_ep(self, ep_name):
        model = self.plugin_list.get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == ep_name:
                return model, iter
            iter = model.iter_next(iter)
        return model, None

    def refresh_plugins_repo(self):
        """Refresh repository plugins"""
        model = self.plugin_list.get_model()
        iter = model.get_iter_first()
        while iter:
            citer = model.iter_children(iter)
            while citer:
                obj = model.get_value(citer, 0)
                if isinstance(obj, etree._Element):
                    model.remove(citer)
                citer = model.iter_next(citer)
            iter = model.iter_next(iter)
        if not self.app.config.get("plugins.repo_enabled"):
            return
        if not os.path.isfile(cf.USER_PLUGIN_REPO):
            if not self.sync_repo_file():
                return
        dom = etree.parse(cf.USER_PLUGIN_REPO)
        for plugin in dom.xpath("//*/plugin"):
            ptype = plugin.get("type")
            model, iter = self._plugin_iter_for_ep(int(ptype))
            if not iter:
                log.error("Invalid plugin type %r" % ptype)
                continue
            citer = model.iter_children(iter)
            skip = False
            while citer:
                x = model.get_value(citer, 0)
                if isclass(x) and issubclass(x, GenericPlugin) \
                and x.id == plugin.get("id"):
                    skip = True
                    break
                elif isinstance(x, etree._Element) \
                and x.get("id") == plugin.get("id"):
                    skip = True
                    break
                citer = model.iter_next(citer)
            if skip:
                continue
            lbl = '<b>[REPO] %s</b>' % plugin.xpath("//*/name")[0].text or _(u"Unknown")
            if plugin.xpath("//*/description"):
                lbl += "\n"+plugin.xpath("//*/description")[0].text
            ico = self.app.load_icon("stock_internet",
                                     gtk.ICON_SIZE_LARGE_TOOLBAR,
                                     gtk.ICON_LOOKUP_FORCE_SVG)
            citer = model.append(iter)
            model.set(citer,
                      0, plugin,
                      1, False,
                      2, lbl,
                      3, ico,
                      4, True)

    def refresh_shortcuts(self):
        model = self.shortcuts_model
        model.clear()
        for group in self.win.ui.get_action_groups():
            if group.get_name() == 'clipboard':
                continue
            iter_ = model.append(None)
            lbl = group.get_data('cf::label') or group.get_name()
            model.set(iter_, 0, lbl, 3, False)
            for action in group.list_actions():
                # Don't display menu items with submenus
                if action.get_name().endswith('menu-action') \
                or action.get_name().startswith('activate-editor'):
                    continue
                citer = model.append(iter_)
                accel_path = action.get_accel_path()
                if accel_path is None:
                    keyval = mods = None
                else:
                    shortcut = gtk.accel_map_lookup_entry(accel_path)
                    if shortcut is not None:
                        keyval, mods = shortcut
                    else:
                        keyval = mods = None
                model.set(citer,
                          0, action.props.label.replace('_', ''),
                          3, True,
                          4, action.props.tooltip,
                          5, action)
                if keyval is not None:
                    model.set(citer, 1, keyval)
                if mods is not None:
                    model.set(citer, 2, mods)
