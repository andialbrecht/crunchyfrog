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

from cf.db import Datasource
from cf.plugins.core import GenericPlugin
from cf.plugins.mixins import InstanceMixin
from cf.ui import dialogs
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
        if not isinstance(obj, Datasource):
            return
        item = gtk.MenuItem(_(u'Open Native Shell'))
        item.show()
        popup.append(item)
        cmd = obj.backend.get_native_shell_command(obj.url)
        if cmd is None:
            item.set_sensitive(False)
        else:
            item.set_sensitive(True)
            item.connect('activate', self.on_start_shell, obj,
                         browser.instance)

    def on_start_shell(self, menuitem, obj, instance):
        view = NativeShell(self.app, instance, obj)
        instance.queries.add_item(view)


try:
    import vte
except ImportError, err:
    NativeShellPlugin.INIT_ERROR = _(u'Please install python-vte.')
    class Dummy(object):
        Terminal = str
    vte = Dummy



class NativeShell(gtk.ScrolledWindow, PaneItem):

    name = _(u'Native Shell')
    icon = 'gnome-terminal'
    detachable = True

    def __init__(self, app, instance, datasource):
        gtk.ScrolledWindow.__init__(self)
        PaneItem.__init__(self, app)
        self.app = app
        self.instance = instance
        self.datasource = datasource
        self.tab_label.set_datasource(datasource)
        self.tab_label.set_text(_(u'Shell') + (': %s' % datasource.public_url))
        self.term = vte.Terminal()
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.add(self.term)
        self.term.show()
        cmd, args = self.datasource.backend.get_native_shell_command(
            self.datasource.url)
        args.insert(0, cmd)
        self.term.connect('child-exited', self.on_child_exited, cmd, args)
        self.term.fork_command(cmd, args)

    def on_child_exited(self, term, cmd, args):
        exit_status = term.get_child_exit_status()
        if exit_status != 0:
            msg = _((u'The command "%(command)s" failed '
                     u'(Exit status: %(status)d).'))
            msg = msg % {'command': cmd, 'status': exit_status}
            gtk.gdk.threads_enter()
            dialogs.error(_(u'Failed'), msg)
            gtk.gdk.threads_leave()
        self.destroy()

    def get_focus_child(self):
        return self.term
