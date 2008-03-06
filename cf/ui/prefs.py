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

"""Preferences"""

import gtk
import gobject
import gnome
import gconf

from gettext import gettext as _

import cf
from cf.ui import GladeWidget

class PreferencesDialog(GladeWidget):
    
    def __init__(self, app):
        GladeWidget.__init__(self, app, "crunchyfrog", "preferences_dialog")
        self.refresh()
        
    def _setup_widget(self):
        self._setup_plugins()
        self._setup_editor()
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
        it = gtk.icon_theme_get_default()
        def get_pb(stock):
            return it.load_icon(stock, 36, gtk.ICON_LOOKUP_FORCE_SVG)
        model.append([0, _(u"General"), get_pb("gtk-execute")])
        model.append([1, _(u"View"), get_pb("gtk-justify-left")])
        model.append([2, _(u"Editor"), get_pb("gtk-edit")])
        model.append([3, _(u"Fonts & Colors"), get_pb("gtk-font")])
        iconview.connect("selection-changed", self.on_editor_selection_changed)
        from cf.ui.editor import USE_GTKSOURCEVIEW2
        if not USE_GTKSOURCEVIEW2:
            self.xml.get_widget("editor_schemes_box").set_sensitive(False)
            self.xml.get_widget("editor_schemes_box").hide()
            # FIXME: Is there really no way to set right margin position on SourceView?
            self.xml.get_widget("editor_right_margin_position_box").set_sensitive(False)
            self.xml.get_widget("editor_right_margin_position_box").hide()
        else:
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
        renderer = gtk.CellRendererPixbuf()
        col.pack_start(renderer, expand=False)
        col.add_attribute(renderer, 'pixbuf', 3)
        renderer = gtk.CellRendererText()
        col.pack_start(renderer, expand=True)
        col.add_attribute(renderer, 'markup', 2)
        self.plugin_list.append_column(col)
        # active
        renderer = gtk.CellRendererToggle()
        renderer.connect("toggled", self.on_plugin_active_toggled)
        col = gtk.TreeViewColumn("", renderer, active=1, visible=4)
        self.plugin_list.append_column(col)
        
    def _setup_connections(self):
        self.app.plugins.connect("plugin-added", self.on_plugin_added)
        self.app.plugins.connect("plugin-removed", self.on_plugin_removed)
        
    def on_editor_open_in_window_toggled(self, toggle):
        self.app.config.set("editor.open_in_window", toggle.get_active())
        
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
        
    def on_editor_selection_changed(self, iconview):
        model = iconview.get_model()
        for path in iconview.get_selected_items():
            iter = model.get_iter(path)
            nb = self.xml.get_widget("editor_notebook")
            nb.set_current_page(model.get_value(iter, 0))
    
    def on_plugin_active_toggled(self, renderer, path):
        iter = self.plugin_model.get_iter(path)
        self.plugin_model.set_value(iter, 1, not renderer.get_active())
        plugin = self.plugin_model.get_value(iter, 0)
        gobject.idle_add(self.app.plugins.set_active, plugin, not renderer.get_active())
        
    def on_plugin_added(self, manager, plugin):
        iter = self.plugin_model.get_iter_first()
        it = gtk.icon_theme_get_default()
        while iter:
            if self.plugin_model.get_value(iter, 0) == plugin._entry_point_group:
                break
            iter = self.plugin_model.iter_next(iter)
        if iter:
            lbl = '<b>%s</b>' % plugin.name or _(u"Unknown")
            if plugin.description:
                lbl += "\n"+plugin.description
            if plugin.icon:
                ico = it.load_icon(plugin.icon, gtk.ICON_SIZE_LARGE_TOOLBAR, gtk.ICON_LOOKUP_FORCE_SVG)
            else:
                ico = None
            citer = self.plugin_model.append(iter)
            self.plugin_model.set(citer,
                      0, plugin,
                      1, self.app.plugins.is_active(plugin),
                      2, lbl,
                      3, ico,
                      4, True)
            
    def on_plugin_removed(self, manager, plugin):
        iter = self.plugin_model.get_iter_first()
        while iter:
            if self.plugin_model.get_value(iter, 0) == plugin._entry_point_group:
                citer = self.plugin_model.iter_children(iter)
                while citer:
                    if self.plugin_model.get_value(citer, 0) == plugin:
                        self.plugin_model.remove(citer)
                        return
                    citer = self.plugin_model.iter_next(citer)
            iter = self.plugin_model.iter_next(iter)
                
    def on_plugin_folder_show(self, *args):
        gnome.url_show(cf.USER_PLUGIN_URI)
        
    def refresh(self):
        self.refresh_editor()
        self.refresh_plugins()
        
    def refresh_editor(self):
        config = self.app.config
        gw = self.xml.get_widget
        gw("editor_open_separate").set_active(config.get("editor.open_in_window"))
        gw("editor_replace_variables").set_data("config_option", "editor.replace_variables")
        gw("editor_replace_variables").set_active(config.get("editor.replace_variables"))
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
        client = gconf.client_get_default()
        default_font = client.get_string("/desktop/gnome/interface/monospace_font_name")
        gw("editor_default_font").set_label(gw("editor_default_font").get_label() % default_font)
        gw("editor_font_box").set_sensitive(not config.get("editor.default_font"))
        gw("editor_font").set_data("config_option", "editor.font")
        gw("editor_font").set_font_name(config.get("editor.font"))
        
    def refresh_plugins(self):
        # Plugins
        model = self.plugin_model
        model.clear()
        it = gtk.icon_theme_get_default()
        for key, value in self.app.plugins.entry_points.items():
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
                if plugin.icon:
                    ico = it.load_icon(plugin.icon, gtk.ICON_SIZE_LARGE_TOOLBAR, gtk.ICON_LOOKUP_FORCE_SVG)
                else:
                    ico = None
                citer = model.append(iter)
                model.set(citer,
                          0, plugin,
                          1, self.app.plugins.is_active(plugin),
                          2, lbl,
                          3, ico,
                          4, True)