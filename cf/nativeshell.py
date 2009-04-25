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

"""Native Shells"""

import gtk
import vte

from cf.db import Datasource
from cf.plugins.core import GenericPlugin
from cf.plugins.mixins import InstanceMixin
from cf.ui.pane import PaneItem


class NativeShellPlugin(GenericPlugin, InstanceMixin):

    id = "crunchyfrog.plugin.nativeshell"
    name = _(u"Native Shell")
    description = _(u"Native Database shells")
    icon = "gnome-terminal"
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://crunchyfrog.googlecode.com"
    version = "0.1"

    def __init__(self, app):
        self._instances = dict()
        self.app = app

    def init_instance(self, instance):
        if instance in self._instances:
            return
        instance.ui.add_ui_from_string(UI)
        group = gtk.ActionGroup('native-shell')
        tooltip = _(u'Access this database through it\'s native shell')
        action = gtk.Action('nativeshell-run', _(u'Open Native Shell'),
                            tooltip, None)
        group.add_action(action)
        action.connect('activate', self.on_start_shell, instance)
        instance.ui.insert_action_group(group)
        sid = instance.browser.connect('object-menu-popup',
                                       self.on_object_menu_popup)
        self._instances[instance] = (sid, [])

    def shutdown(self):
        while self._instances:
            instance, args = self._instances.popitem()
            sid, views = args
            for view in views:
                view.destroy()
            instance.browser.disconnect(sid)

    def on_object_menu_popup(self, browser, popup, obj):
        action = browser.instance._get_action('nativeshell-run')
        action.set_data('cf::native-shell-obj', None)
        if not isinstance(obj, Datasource):
            action.set_visible(False)
            return
        action.set_visible(True)
        cmd = obj.backend.get_native_shell_command(obj.url)
        if cmd is None:
            action.set_sensitive(False)
        else:
            action.set_sensitive(True)
            action.set_data('cf::native-shell-obj', obj)

    def on_start_shell(self, action, instance):
        obj = action.get_data('cf::native-shell-obj')
        view = NativeShell(self.app, instance, obj)
        instance.queries.add_item(view)


class NativeShell(vte.Terminal, PaneItem):

    name = _(u'Native Shell')
    icon = 'gnome-terminal'
    detachable = True

    def __init__(self, app, instance, datasource):
        vte.Terminal.__init__(self)
        self.app = app
        self.instance = instance
        self.datasource = datasource
        cmd, args = self.datasource.backend.get_native_shell_command(
            self.datasource.url)
        args.insert(0, cmd)
        self.fork_command(cmd, args)
        self.connect('child-exited', self.on_child_exited)

    def on_child_exited(self, term):
        self.destroy()


UI = '''
<popup name="NavigatorPopup">
  <menuitem name="NativeShell" action="nativeshell-run" />
</popup>
'''
