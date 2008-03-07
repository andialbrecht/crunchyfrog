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

"""Mixin classes for plugins

Plugins can use this classes to provide a certain behaviour
or to have special attributes. For example, if a plugin needs to
add an item to the menubar of an instance, the plugin must connect
to the ``instance-created`` signal and have to fetch the menubar from
the instances widget tree. The `MenubarMixin`_ provides a 
``menubar_load(menubar, instance)`` method which is automatically called
by the `plugin manager`_. So you don't need to pay attention on instance
creation and can focus on the menubar itself when your plugin implements
these methods.

.. _MenubarMixin: cf.plugins.mixins.MenubarMixin.html
.. _plugin manager: cf.plugins.core.PluginManager.html
"""

class InstanceMixin(object):
    """Instance relation
    
    This mixin can be used by plugins that require a relation to a 
    running instance.
    """
    
    def init_instance(self, instance):
        """Called on instance creation.
        
        :Parameter:
            instance
                the created instance
        """
        pass
    
class MenubarMixin(InstanceMixin):
    """Modify the applications main menu
    
    ``menubar_load`` is called on activation for each instance and
    if a new instance is created.
    
    ``menubar_unload`` is called when the plugin is deactivated for 
    each instance.
    """
    
    def menubar_load(self, menubar, instance):
        """Add items to the main menu
        
        :Parameter:
            menubar
                Main menu (``gtk.MenuBar``)
            instance
                An instance
        """
        pass
    
    def menubar_unload(self, menubar, instance):
        """Remove items to the main menu
        
        :Parameter:
            menubar
                Main menu (``gtk.MenuBar``)
            instance
                An instance
        """
        pass
    
class EditorMixin(InstanceMixin):
    """Editor relation
    
    This mixin can be used to keep track of the current editor.
    """
    
    def set_editor(self, editor, instance):
        """Called when an editor gets activated
        
        :Parameter:
            editor
                Active editor or ``None``
            instance
                An instance
        """
        pass
    
class UserDBMixin:
    """User database access
    
    For more information about how use the user database see `UserDB`_.
    
    Sets ``userdb`` property.
    
    .. _`UserDB`: cf.userdb.UserDB.html
    """
    
    def userdb_set(self, userdb):
        """Associates the userdb with the plugin
        
        .. Warning:: This method shouldn't be subclassed by plugins.
        """
        self.set_data("userdb", userdb)
    
    def userdb_get(self):
        """Returns the associated userdb"""
        return self.get_data("userdb")
    
    userdb = property(fget=userdb_get)
    
    def userdb_init(self):
        """Called when a plugin is activated
        
        This is the right place to create tables, check table versions
        and doing table upgrades.
        """
        pass