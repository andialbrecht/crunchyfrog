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

"""SQL-specific TextView

This module provides a SQL-specific TextView widget. Depending on
your system it is a gtksourceview2 or gtksourceview implementation.

Both implementations inherit ``SQLViewBase`` which connects to the
configuration instance to update some options when they are changed
through the preferences dialog.

Example usage
=============

    .. sourcecode:: python
    
        >>> from cf.ui.widgets.sqlview import SQLView
        >>> import gtk
        >>> w = gtk.Window()
        >>> sw = gtk.ScrolledWindow()
        >>> view = SQLView(app)
        >>> view.get_buffer().set_text("select * from foo")
        >>> sw.add(view)
        >>> w.add(sw)
        >>> w.show_all()
        
"""

import gconf
import gtk
import gobject
import pango
   
class SQLViewBase(object):
    """Base class for SQLView implementations"""
    
    def __init__(self, app):
        """
        This constructor takes one argument:
        
        :Parameter:
            app
                `CFApplication`_ instance
                
        .. _CFApplication: cf.app.CFApplication.html
        """
        self.app = app
        self.app.config.connect("changed", self.on_config_changed)
        self.update_textview_options()
        
    def on_config_changed(self, config, option, value):
        if option.startswith("editor."):
            gobject.idle_add(self.update_textview_options)
            
    def update_textview_options(self):
        """Updates the textview settings"""
        conf = self.app.config
        buffer = self.get_buffer()
        if conf.get("editor.wrap_text"):
            if conf.get("editor.wrap_split"):
                self.set_wrap_mode(gtk.WRAP_CHAR)
            else:
                self.set_wrap_mode(gtk.WRAP_WORD)
        else:
            self.set_wrap_mode(gtk.WRAP_NONE)
        self.set_show_line_numbers(conf.get("editor.display_line_numbers"))
        self.set_highlight_current_line(conf.get("editor.highlight_current_line"))
        self.set_insert_spaces_instead_of_tabs(conf.get("editor.insert_spaces"))
        self.set_auto_indent(conf.get("editor.auto_indent"))
        if conf.get("editor.default_font"):
            client = gconf.client_get_default()
            font = client.get_string("/desktop/gnome/interface/monospace_font_name")
        else:
            font = conf.get("editor.font")
        self.modify_font(pango.FontDescription(font))
        
try:
    import gtksourceview2
    USE_GTKSOURCEVIEW2 = True
    class SQLView(gtksourceview2.View, SQLViewBase):
        """SQLViewBase implementation"""
        def __init__(self, app):
            gtksourceview2.View.__init__(self)
            buffer = gtksourceview2.Buffer()
            self.set_buffer(buffer)
            lm = gtksourceview2.language_manager_get_default()
            buffer.set_language(lm.get_language("sql"))
            SQLViewBase.__init__(self, app)
            
        def update_textview_options(self):
            SQLViewBase.update_textview_options(self)
            conf = self.app.config
            buffer = self.get_buffer()
            # gtksourceview2 specific
            self.set_show_right_margin(conf.get("editor.right_margin"))
            self.set_right_margin_position(conf.get("editor.right_margin_position"))
            buffer.set_highlight_matching_brackets(conf.get("editor.bracket_matching"))
            self.set_tab_width(conf.get("editor.tabs_width"))
            sm = gtksourceview2.style_scheme_manager_get_default()
            scheme = sm.get_scheme(conf.get("editor.scheme"))
            buffer.set_style_scheme(scheme)
            
except ImportError:
    USE_GTKSOURCEVIEW2 = False
    import gtksourceview
    class SQLView(gtksourceview.SourceView, SQLViewBase):
        """SQLViewBase implementation"""
        def __init__(self, app):
            gtksourceview.SourceView.__init__(self)
            buffer = gtksourceview.SourceBuffer()
            self.set_buffer(buffer)
            buffer.set_highlight(True)
            lm = gtksourceview.SourceLanguagesManager()
            for lang in lm.get_available_languages():
                if lang.get_id() == "SQL":
                    buffer.set_language(lang)
                    break
            SQLViewBase.__init__(self, app)
                
        def update_textview_options(self):
            SQLViewBase.update_textview_options(self)
            conf = self.app.config
            buffer = self.get_buffer()
            # gtksourceview specific
            self.set_show_margin(conf.get("editor.right_margin"))
            #self.set_right_margin(conf.get("editor.right_margin_position"))
            buffer.set_check_brackets(conf.get("editor.bracket_matching"))
            self.set_tabs_width(conf.get("editor.tabs_width"))