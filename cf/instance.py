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

"""Instance class"""

import gtk
import gtk.glade
import gnome
import gnomevfs
import gobject

import os

from gettext import gettext as _

from cf import release
from cf.ui import GladeWidget
from cf.ui import pdock
from cf.ui.browser import Browser
from cf.ui.datasources import DatasourceManager
from cf.ui.editor import Editor, EditorWindow
from cf.ui.queries import QueriesNotebook
from cf.ui.statusbar import CFStatusbar
from cf.ui.toolbar import CFToolbar
from cf.ui.widgets import ConnectionButton

class CFInstance(GladeWidget):
    
    def __init__(self, app):
        """
        The constructor of this class takes one argument:
        
        :Parameter:
            app
                `CFApplication`_ instance
                
        .. _CFApplication: cf.app.CFApplication.html
        """
        GladeWidget.__init__(self, app, "crunchyfrog", "mainwindow")
        self._editor = None
        
    def _setup_widget(self):
        # Window state
        if self.app.config.get("gui.width", -1) != -1:
            self.widget.resize(self.app.config.get("gui.width"),
                               self.app.config.get("gui.height"))
        if self.app.config.get("gui.maximized", False):
            self.widget.maximize()
        # Tooltips
        self.tt = gtk.Tooltips()
        # Toolbar
        self.toolbar = CFToolbar(self.app, self.xml)
        self.toolbar.show_all()
        # Statusbar
        self.statusbar = CFStatusbar(self.app, self.xml)
        # Dock
        self.dock = pdock.Dock()
        box = self.xml.get_widget("box_main")
        box.pack_start(self.dock, True, True)
        box.reorder_child(self.dock, 2)
        self.dock.show_all()
        # Queries
        self.queries = QueriesNotebook(self.app, self)
        item = pdock.DockItem(self.dock, "queries", self.queries, _(u"Queries"),
                              "gtk-edit", None, pdock.DOCK_ITEM_BEH_LOCKED)
        self.dock.add_item(item)
        # Browser
        self.browser = Browser(self.app, self)
        item = pdock.DockItem(self.dock, "browser", self.browser, _(u"Navigator"), 
                              "gtk-find", gtk.POS_LEFT, pdock.DOCK_ITEM_BEH_CANT_CLOSE)
        self.dock.add_item(item)
        self.browser.set_data("dock_item", item)
        gobject.idle_add(self.xml.get_widget("mn_navigator").set_active, self.app.config.get("navigator.visible", True))
    
    def _init_ui(self, argv):
        pass
    
    def on_about(self, *args):
        def open_url(dialog, url):
            gnome.url_show(url)
        gtk.about_dialog_set_url_hook(open_url)
        dlg = gtk.AboutDialog()
        dlg.set_name(release.name)
        dlg.set_version(release.version)
        dlg.set_copyright(release.copyright)
        dlg.set_license(release.license)
        dlg.set_website(release.url)
        dlg.set_website_label(release.url)
        dlg.set_logo_icon_name(release.appname)
        dlg.set_program_name(release.appname)
        dlg.run()
        dlg.destroy()
        
    def on_commit(self, *args):
        if not self._editor:
            return 
        gobject.idle_add(self._editor.commit)
        
    def on_rollback(self, *args):
        if not self._editor:
            return
        gobject.idle_add(self._editor.rollback)
        
    def on_begin_transaction(self, *args):
        if not self._editor:
            return
        gobject.idle_add(self._editor.begin_transaction)
        
    def on_configure_event(self, win, event):
        config = self.app.config
        if not config.get("gui.maximized"):
            config.set("gui.width", event.width)
            config.set("gui.height", event.height)
            
    def _get_clipboard(self):
        display = gtk.gdk.display_manager_get().get_default_display()
        return gtk.Clipboard(display, "CLIPBOARD")
            
    def on_copy(self, *args):
        if not self._editor:
            return
        self._editor.textview.get_buffer().copy_clipboard(self._get_clipboard())
        
    def on_paste(self, *args):
        if not self._editor:
            return 
        self._editor.textview.get_buffer().paste_clipboard(self._get_clipboard(), None, True)
        
    def on_cut(self, *args):
        if not self._editor:
            return
        self._editor.textview.get_buffer().cut_clipboard(self._get_clipboard(), True)
        
    def on_delete(self, *args):
        if not self._editor:
            return
        self._editor.textview.get_buffer().delete_selection(True, True)
            
    def on_datasource_manager(self, *args):
        dlg = DatasourceManager(self.app)
        dlg.run()
        dlg.destroy()
        
    def on_execute_query(self, *args):
        gobject.idle_add(self._editor.execute_query)
        
    def on_help(self, *args):
        self.show_help()
        
    def on_navigator_toggled(self, menuitem):
        if menuitem.get_active():
            self.browser.get_data("dock_item").show()
            self.app.config.set("navigator.visible", True)
        else:
            self.browser.get_data("dock_item").hide()
            self.app.config.set("navigator.visible", False)
    
    def on_new_instance(self, *args):
        self.app.new_instance(tuple())
        
    def on_open_file(self, *args):
        dlg = gtk.FileChooserDialog(_(u"Select file"),
                            self.widget,
                            gtk.FILE_CHOOSER_ACTION_OPEN,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                             gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dlg.set_current_folder(self.app.config.get("editor.recent_folder", ""))
        filter = gtk.FileFilter()
        filter.set_name(_(u"All files (*)"))
        filter.add_pattern("*")
        dlg.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name(_(u"SQL files (*.sql)"))
        filter.add_pattern("*.sql")
        dlg.add_filter(filter)
        dlg.set_filter(filter)
        if dlg.run() == gtk.RESPONSE_OK:
            self.new_editor(dlg.get_filename())
            self.app.config.set("editor.recent_folder", dlg.get_current_folder())
        dlg.destroy()
        
    def on_save_file(self, *args):
        if not self._editor:
            return 
        self._editor.save_file()
        
    def on_save_file_as(self, *args):
        if not self._editor:
            return
        self._editor.save_file_as()
        
    def on_report_problem(self, *args):
        gobject.idle_add(self.open_website, "http://code.google.com/p/crunchyfrog/issues/list")
        
    def on_open_devpages(self, *args):
        gobject.idle_add(self.open_website, "http://crunchyfrog.googlecode.com")
        
    def on_open_helptranslate(self, *args):
        gobject.idle_add(self.open_website, "https://translations.launchpad.net/crunchyfrog/trunk/")
        
    def on_preferences(self, *args):
        self.app.preferences_show()
        
    def on_query_new(self, *args):
        self.new_editor()
        
    def on_quit(self, *args):
        self.widget.destroy()
        
    def on_window_state_event(self, win, event):
        config = self.app.config
        bit = gtk.gdk.WINDOW_STATE_MAXIMIZED.value_names[0] in event.new_window_state.value_names
        config.set("gui.maximized", bit)
        
    def new_editor(self, fname=None):
        """Creates a new SQL editor
        
        :Parameter:
            fname
                If given, the file ``fname`` is opened with this editor
        :Returns: `Editor`_ instance
        
        .. _Editor: cf.ui.editor.Editor.html
        """
        editor = Editor(self.app, self)
        if fname:
            if fname.startswith("file://"):
                fname = gnomevfs.get_local_path_from_uri(fname)
            editor.set_filename(fname)
        if self.app.config.get("editor.open_in_window"):
            editor.show_in_separate_window()
        else:
            self.queries.attach(editor)
        editor.show_all()
        return editor
        
    def open_website(self, url):
        gnome.url_show(url)
        
    def set_editor_active(self, editor, active):
        if not active:
            editor = None
        self._editor = editor
        self.toolbar.set_editor(editor)
        self.app.plugins.editor_notify(editor, self)
        
    def get_editor(self):
        """Returns the active editor
        
        :Returns: editor instance or ``None``
        """
        return self._editor
        
    def show_help(self, topic=None):
        gnome.help_display(release.appname, topic)