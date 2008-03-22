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

"""Schema browsing base classes"""

import gobject

from gettext import gettext as _

class SchemaProvider(gobject.GObject):
    
    def __init__(self):
        self.__gobject_init__()
        
    def fetch_children(self, connection, parent):
        return []
    
    def get_details(self, connection, obj):
        return None
    
class Node(gobject.GObject):
    name = None
    description = None
    icon = "gtk-missing-image"
    has_children = True
    has_details = False
    
    def __init__(self, name=None, description=None, *args, **kwargs):
        self.__gobject_init__()
        if name:
            self.name = name
        self.description = description
        if kwargs.has_key("has_details"):
            self.has_details = kwargs.pop("has_details")
        for key, value in kwargs.items():
            self.set_data(key, value)
    
class Collection(Node):
    icon = "gtk-open"
    
class SchemaCollection(Collection):
    name = _(u"Schematas")
    
class Schema(Node):
    name = _(u"Schema")
    icon = "gtk-open"
    
class TableCollection(Collection):
    name = _(u"Tables")
    icon = "stock_data-tables"
    
class Table(Node):
    name = _(u"Table")
    icon = "stock_data-table"
    
class ColumnCollection(Collection):
    name = _(u"Columns")
    
class Column(Node):
    name = _(u"Column")
    icon = "stock_insert-columns"
    has_children = False
    
class ViewCollection(Collection):
    name = _(u"Views")
    icon = "stock_data-tables"
    
class View(Node):
    name = _(u"View")
    icon = "stock_data-table"
    
class SequenceCollection(Collection):
    name = _(u"Sequences")
    icon = "stock_sort-column-ascending"
    
class Sequence(Node):
    name = _(u"Sequence")
    icon = "stock_sort-row-ascending"
    has_children = False
    
class FunctionCollection(Collection):
    name = _(u"Functions")
    icon = "stock_script"
    
class Function(Node):
    name = _(u"Function")
    icon = "stock_macro-check-brackets"
    has_children = False
    
class PackageCollection(Collection):
    name = _(u"Packages")
    
class Package(Node):
    name = _(u"Package")
    icon = "gnome-mime-application-x-archive"
        
class ConstraintCollection(Collection):
    name = _(u"Constraints")
    
class Constraint(Node):
    name = _(u"Contraint")
    icon = "gtk-spell-check"
    
class IndexCollection(Collection):
    name = _(u"Indexes")
    
class Index(Node):
    name = _(u"Index")
    icon = "stock_navigator-indexes"
    has_children = False