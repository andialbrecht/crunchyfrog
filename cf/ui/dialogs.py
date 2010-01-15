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

"""Simple message dialogs."""

from gettext import gettext as _

import gobject
import gtk


DIALOG_TITLES = {
    gtk.STOCK_DIALOG_ERROR: _(u'An error occurred'),
    gtk.STOCK_DIALOG_WARNING: _(u'Warning'),
    gtk.STOCK_DIALOG_INFO: _(u'Information'),
}


def _run_dialog(short, long=None, parent=None, buttons=gtk.BUTTONS_NONE,
                dlg_type=gtk.STOCK_DIALOG_INFO, title=None):
    if dlg_type == gtk.STOCK_DIALOG_ERROR:
        dlg_type2 = gtk.MESSAGE_ERROR
    elif dlg_type == gtk.STOCK_DIALOG_WARNING:
        dlg_type2 = gtk.MESSAGE_WARNING
    elif dlg_type == gtk.STOCK_DIALOG_QUESTION:
        dlg_type2 = gtk.MESSAGE_QUESTION
    else:
        dlg_type2 = gtk.MESSAGE_INFO
    if title is None:
        title = DIALOG_TITLES.get(dlg_type, 'CrunchyFrog')
    dlg = gtk.MessageDialog(parent,
                            gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                            dlg_type2, buttons)
    short = gobject.markup_escape_text(short)
    dlg.set_markup('<b>%s</b>' % short)
    if long is not None:
        dlg.format_secondary_markup(gobject.markup_escape_text(long))
    img = gtk.image_new_from_stock(dlg_type, gtk.ICON_SIZE_DIALOG)
    dlg.set_image(img)
    dlg.set_title(title)
    dlg.set_icon_name('crunchyfrog')
    img.show()
    ret = dlg.run()
    dlg.destroy()
    return ret


def error(short, long=None, parent=None, buttons=gtk.BUTTONS_OK):
    return _run_dialog(short, long, parent, buttons, gtk.STOCK_DIALOG_ERROR)

def warning(short, long=None, parent=None, buttons=gtk.BUTTONS_OK):
    return _run_dialog(short, long, parent, buttons, gtk.STOCK_DIALOG_WARNING)

def yesno(short, long=None, parent=None, buttons=gtk.BUTTONS_YES_NO):
    return _run_dialog(short, long, parent, buttons, gtk.STOCK_DIALOG_QUESTION)

def info(short, long=None, parent=None, buttons=gtk.BUTTONS_OK):
    return _run_dialog(short, long, parent, buttons, gtk.STOCK_DIALOG_INFO)

def password(title, msg=None, parent=None):
    dlg = gtk.MessageDialog(parent,
                            gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                            gtk.MESSAGE_QUESTION,
                            gtk.BUTTONS_OK_CANCEL)
    title = gobject.markup_escape_text(title)
    dlg.set_markup('<b>%s</b>' % title)
    dlg.set_title(_(u'Password required'))
    dlg.set_icon_name('crunchyfrog')
    if msg is not None:
        dlg.format_secondary_markup(msg)
    hbox = gtk.HBox()
    hbox.set_border_width(6)
    hbox.set_spacing(7)
    hbox.show()
    dlg.vbox.pack_start(hbox)

    label = gtk.Label(_('Password:'))
    label.show()
    hbox.pack_start(label, False, False)

    entry = gtk.Entry()
    entry.set_invisible_char(u'\u2022')
    entry.set_visibility(False)
    entry.show()
    hbox.pack_start(entry)

    if dlg.run() == gtk.RESPONSE_OK:
        ret = entry.get_text()
    else:
        ret = None
    dlg.destroy()
    return ret
