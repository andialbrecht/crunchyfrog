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

"""SQL formatter plugin

The printsql module is based on the work of Peter Bengtsson.
Visit his blog for details: http://www.peterbe.com/Pretty-print-SQL-script
"""

import gtk

from cf.plugins.core import GenericPlugin, PLUGIN_TYPE_EDITOR
from cf.plugins.mixins import MenubarMixin, EditorMixin
from cf.ui.widgets import CustomImageMenuItem

from gettext import gettext as _

from printsql import printsql

class SQLFormatterPlugin(GenericPlugin, MenubarMixin, EditorMixin):
    id = "cf.editor.sqlformat"
    plugin_type = PLUGIN_TYPE_EDITOR
    name = "SQL Formatter"
    description = "Formats the statement in current editor"
    icon = "stock_autoformat"
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://cf.andialbrecht.de"
    version = "0.1"
    
    def __init__(self, *args, **kw):
        GenericPlugin.__init__(self, *args, **kw)
        self._mn_items = dict()
    
    def menubar_load(self, menubar, instance):
        edit_menu = instance.xml.get_widget("mn_edit").get_submenu()
        sep = gtk.SeparatorMenuItem()
        sep.show()
        edit_menu.append(sep)
        item = CustomImageMenuItem("stock_autoformat", _(u"Format SQL"))
        item.set_sensitive(False)
        item.connect("activate", self.on_format_sql, instance)
        item.show()
        edit_menu.append(item)
        self._mn_items[instance] = [sep, item]
        
    def menubar_unload(self, menubar, instance):
        for item in self._mn_items[instance]:
            item.get_parent().remove(item)
            item.destroy()
        del self._mn_items[instance]
        
    def set_editor(self, editor, instance):
        if not self._mn_items.has_key(instance):
            return
        self._mn_items[instance][1].set_sensitive(bool(editor))
        
    def on_format_sql(self, menuitem, instance):
        editor = instance.get_editor()
        if not editor:
            return
        sql = editor.get_text()
        editor.set_text(printsql(sql))