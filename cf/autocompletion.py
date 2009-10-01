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

"""Autocompletion support for SQL editor.

The functions in this module provide autocompletion support for SQL editor
widgets.

The feature is enabled by calling the :meth:`setup` function. It then
automatically connects to instance and editor creation and to relevant
config changes.
"""

import itertools
from gettext import gettext as _

import gobject
import gtk
import pango

import sqlparse.keywords

from cf import db


SQL_KEYWORDS = set(tuple(sqlparse.keywords.KEYWORDS))
SQL_KEYWORDS.update(tuple(sqlparse.keywords.KEYWORDS_COMMON))


def setup(app):
    """Setup autocompletion feature.

    Connect to 'instance-created' and 'changed' (config) signal.

    :param app: Application instance.
    """
    app.cb.connect('instance-created', instance_created, app)
    app.config.connect('changed', on_config_changed)


def instance_created(callbacks, window, app):
    """Adds UI definition and actions to the new instance."""
    group = [x for x in window.ui.get_action_groups()
             if x.get_name() == 'editor'][0]
    group.add_actions([('query-autocomplete', None,
                        _(u'_Auto-Complete'), '<control>space',
                        None, run_action)], window)
    window.ui.add_ui_from_string(UI)
    window.connect('editor-created', on_editor_created)


def run_action(action, window):
    """Run the autocompletion action."""
    editor = window.get_active_editor()
    if editor is None:
        return
    if editor.textview.get_data('cf::ac_window') is not None:
        return
    editor_autocomplete(editor)


def editor_autocomplete(editor, popup=None, matches=None):
    """Implementation of the autocompletion feature.

    :param editor: SQLEditor instance.
    :param popup: The popup window. If `None` (default) a new window is
      created.
    :param matches: If given, the completions are set from these matches.
      Otherwise the possible completions are build within this function.
      The default is `None`.
    """
    if matches is None:
        matches = get_matches(editor)
    if matches is None:
        return
    scores = matches.keys()
    if not scores:
        if popup is not None:
            destroy_popup(editor.textview, popup)
        return
    buffer_ = editor.textview.buffer
    start, end = get_fragment_bounds(buffer_)
    iter_rect = editor.textview.get_iter_location(end)
    x, y = editor.textview.window.get_origin()
    y2, height = editor.textview.get_line_yrange(end)
    left_window = editor.textview.get_window(gtk.TEXT_WINDOW_LEFT)
    if popup is None:
        popup = editor.textview.get_data('cf::ac_window')
        if popup is None:
            popup = create_popup_window(editor)
    model = popup.get_data('model')
    treeview = popup.get_data('treeview')
    popup.move(x+iter_rect.x+left_window.get_size()[0], y+iter_rect.y+height)
    populate_model(model, matches)
    iter_ = model.get_iter_first()
    selection = treeview.get_selection()
    selection.select_iter(iter_)


def _is_keyword(value):
    """Return True if value is a SQL keyword."""
    return value.upper() in SQL_KEYWORDS


def editor_autocomplete_advanced(editor):
    """Implementation of advanced autocompletion (tab-completion).

    If there's exactly one match, the match is applied automatically.
    Otherwise the usual :meth:`editor_autocompletion` implementation is
    called.

    :param editor: SQLEditor instance.
    """
    matches = get_matches(editor)
    if matches is None:
        return False
    completions = set()
    for value in matches.itervalues():
        for compl in value:
            completions.add(compl[1][0])
    if len(completions) == 0:
        return True
    elif len(completions) != 1:
        editor_autocomplete(editor, matches=matches)
        return True
    value = completions.pop()
    _apply_selection(editor, value, add_blank=_is_keyword(value))
    return True


# ----
# Completion Popup
# ----

def create_popup_window(editor):
    """Create a new popup window for an editor.

    The created popup window is set as widget data to *editor*.

    :param editor: SQLEditor instance.
    """
    w = gtk.Window(gtk.WINDOW_POPUP)
    w.set_name('gtk-tooltips')
    w.set_border_width(4)
    w.set_decorated(False)
    w.set_app_paintable(True)
    w.connect('expose-event', popup_window_expose)
    cpl_list = gtk.TreeView()
    cpl_list.set_headers_visible(False)
    model = gtk.ListStore(str, str, str, str)
    model.set_data('cf::bgcolor1', w.get_style().bg[gtk.STATE_NORMAL])
    model.set_data('cf::bgcolor2', w.get_style().bg[gtk.STATE_PRELIGHT])
    cpl_list.set_model(model)
    cpl_list.set_style(w.get_style())
    col = gtk.TreeViewColumn(None, gtk.CellRendererText(), markup=0,
                             background=2)
    col.set_expand(True)
    cpl_list.append_column(col)
    col = gtk.TreeViewColumn(None, gtk.CellRendererText(), markup=1,
                             background=2)
    col.set_expand(False)
    cpl_list.append_column(col)
    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
    sw.add(cpl_list)
    w.add(sw)
    w.resize(350, 160)
    w.show_all()
    w.set_data('model', model)
    w.set_data('treeview', cpl_list)
    textview = editor.textview
    textview.set_data('cf::ac_window', w)
    sigs = []
    sigs.append(textview.connect('key-press-event',
                                 editor_key_pressed, editor, w))
    sigs.append(textview.connect('delete-event',
                                 lambda x, e: destroy_popup(textview, w)))
    sigs.append(textview.connect('button-press-event',
                                 lambda x, e: destroy_popup(textview, w)))
    sigs.append(textview.connect('scroll-event',
                                 lambda x, e: destroy_popup(textview, w)))
    sigs.append(textview.connect('focus-out-event',
                                 lambda x, e: destroy_popup(textview, w)))
    textview.set_data('cf::autocomplete_sigs', sigs)
    return w


def popup_window_expose(window, event):
    """Draw a flat box around the popup window on expose event.

    This makes it more look like a 'real' tooltip.
    """
    w, h = window.get_size()
    window.style.paint_flat_box(window.window, gtk.STATE_NORMAL,
                                gtk.SHADOW_OUT, None, window,
                                'tooltip', 0, 0, w, h)


def destroy_popup(textview, window):
    """Destroy and unregister the popup window."""
    sigs = textview.get_data('cf::autocomplete_sigs')
    if sigs is None:
        return
    for sig in sigs:
        textview.disconnect(sig)
    textview.set_data('cf::autocomplete_sigs', None)
    textview.set_data('cf::ac_window', None)
    window.destroy()


def populate_model(model, matches):
    """Populate a ListStore with matches."""
    model.clear()
    color1 = model.get_data('cf::bgcolor1')
    color2 = model.get_data('cf::bgcolor2')
    colors = itertools.cycle([color1, color2])
    scores = list(matches)
    scores.sort()
    for score in scores:
        xmatches = matches[score]
        xmatches.sort(key=lambda x: x[1][0])
        for match in xmatches:
            hint = '<i>%s</i>' % gobject.markup_escape_text(match[1][1])
            sol = ''
            for idx, char in enumerate(match[1][0]):
                if idx in match[0]:
                    tmp = '<b>%s</b>'
                else:
                    tmp = '%s'
                sol += tmp % gobject.markup_escape_text(char)
            model.append([sol, hint, colors.next(), match[1][0]])


def select_offset(popup, offset):
    """Select another item in the completion list.

    :param popup: The popup window.
    :param offset: Item index relative to the selected item.
    """
    treeview = popup.get_data('treeview')
    selection = treeview.get_selection()
    model, iter_ = selection.get_selected()
    if iter_ is None:
        iter_ = model.get_iter_first()
    row = model.get_path(iter_)[0]
    row += offset
    if row < 0:
        row = 0
    try:
        iter_ = model.get_iter(row)
    except ValueError:
        # end of completion list reached.
        # maybe this could be catched earlier be looking at the actual
        # number of rows.
        iter_ = model.get_iter_first()
    selection.select_iter(iter_)
    treeview.scroll_to_cell(row)


def apply_selection(popup, editor):
    """Applies the selected item."""
    treeview = popup.get_data('treeview')
    selection = treeview.get_selection()
    model, iter_ = selection.get_selected()
    value = model.get_value(iter_, 3)
    _apply_selection(editor, value)
    destroy_popup(editor.textview, popup)


# ----
# Helper functions to find and build the possible completions
# ----

def build_completions(editor, fragment):
    """Build the common completions.

    The returned list contains the names of database objects if the editor
    has a connection and meta information. Additionally the list contains
    SQL keywords.

    The returned list is a list of 2-tuples (completion, description) where
    description describes the object (e.g. 'Keyword', 'Table', 'Column'...).

    :param editor: SQLEditor instance.
    :param fragment: The fragment that should be completed.
    """
    ret = []
    # objects
    if editor.connection and editor.connection.meta:
        meta = editor.connection.meta
        [ret.append((obj.get_full_name(), obj.typestr))
         for obj in meta.find(name__ilike=fragment,
                              cls=(db.objects.Table,
                                   db.objects.View,
                                   db.objects.Sequence,
                                   db.objects.Schema))]
    # keywords
    kwds = tuple(sqlparse.keywords.KEYWORDS_COMMON)
    kwds += tuple(sqlparse.keywords.KEYWORDS)
    [ret.append((kwd, _(u'Keyword')))
                for kwd in kwds]
    return ret


def find_matches(completions, fragment):
    """Find matches in the list of completions.

    The function returns a dictionary with the score determined by
    :meth:`get_score` as keys. The value is a list of entries in the form
    (indexes, (solution, description)) where *indexes* is again a 2-tuple
    defining the start and end index that's needed from *solution* to
    complete *fragment*, *solution* and *description* is the 2-tuple
    as returned by :meth:`build_completions`.
    """
    ret = {}
    for solution, comment in completions:
        score, indexes = get_score(solution, fragment)
        if score is None:
            continue
        tmp = ret.get(score, [])
        tmp.append((indexes, (solution, comment)))
        ret[score] = tmp
    return ret


def find_identifier(parsed, name=None):
    """Return the real name for an aliased identifier in a statement.

    :param parsed: Parsed SQL statement.
    :param name: Name to find.
    """

    def _collect_identifiers(tlist):
        for item in tlist:
            if isinstance(item, sqlparse.engine.grouping.Identifier):
                real_name = item.get_real_name()
                yield (item.get_alias() or real_name, real_name)
            elif item.is_group():
                for item in _collect_identifiers(item.tokens):
                    yield item

    # Cleanup aliases in temporary dict.
    # As we return the first match, we must take care that aliased names
    # are resolved.
    items = {}
    for alias, real_name in _collect_identifiers(parsed.tokens):
        if (alias in items
            and items[alias] == alias):
            items[alias] = real_name
        elif alias not in items:
            items[alias] = real_name
    if name is None:
        return items
    # Now return first match from dict.
    for alias, real_name in items.iteritems():
        if alias == name:
            return real_name


def get_score(solution, fragment):
    """Get score for solution."""
    solution = solution.lower()
    fragment = fragment.lower()
    try:
        start = solution.index(fragment)
    except ValueError:
        return None, None
    return start, [start+i for i in range(len(fragment))]


def get_completions_from_identifiers(editor):
    """Similar to get_completions but only with children of an identifier."""
    bounds = editor.textview.get_current_statement()
    meta = editor.connection.meta
    buffer_ = editor.textview.buffer
    completions = []
    if bounds:
        parsed = sqlparse.parse(buffer_.get_text(*bounds))[0]
        for alias, real_name in find_identifier(parsed).iteritems():
            for obj in meta.find(name=real_name):
                if obj.typeid in ('table', 'view'):
                    [completions.append((c.name, c.typestr))
                     for c in obj.columns.get_children()]
    return completions


def get_matches(editor):
    """Get possible completions."""
    buffer_ = editor.textview.buffer
    start, end = get_fragment_bounds(buffer_)
    fragment = buffer_.get_text(start, end)
    completions = None
    matches = None
    if len(fragment) == 0 and editor.connection and editor.connection.meta:
        completions = get_completions_from_identifiers(editor)
        matches = find_matches(completions, '')
    elif len(fragment) < 2:
        popup = editor.textview.get_data('cf::ac_window')
        if popup is not None:
            destroy_popup(editor.textview, popup)
        return
    if '.' in fragment and editor.connection and editor.connection.meta:
        parent_name, rest = fragment.split('.', 1)
        bounds = editor.textview.get_current_statement()
        if bounds:
            parsed = sqlparse.parse(buffer_.get_text(*bounds))[0]
            parent = find_identifier(parsed, parent_name)
            for obj in editor.connection.meta.find(name=parent):
                if obj is not None:
                    if obj.typeid == 'table':
                        completions = [(c.name, c.typestr)
                                       for c in obj.columns.get_children()]
                    elif obj.typeid == 'schema':
                        completions = [(c.name, c.typestr)
                                       for c in obj.tables.get_children()+
                                   obj.views.get_children()]
                if completions:
                    matches = find_matches(completions, rest)
    if completions is None:
        completions = build_completions(editor, fragment)
        matches = find_matches(completions, fragment)
    return matches


def get_fragment_bounds(buffer_, replace_mode=False, value=None):
    """Return start and end iter for fragment bounds.

    *end* is usually the current cursor position and *start* is much
    like backward_word_start() except that it respects some SQL specific
    stuff.
    """
    end = buffer_.get_iter_at_mark(buffer_.get_insert())
    start = end.copy()
    prev = start.copy()
    dot_start = None
    dot_count = 0
    while not prev.starts_line() and not prev.is_start():
        prev.backward_char()
        char = buffer_.get_text(prev, start)
        if char.isalnum() or char in '._"':
            if char == '.' and replace_mode:
                dot_count += 1
                if value is not None and dot_count > value.count("."):
                    return start, end
            start.backward_char()
        else:
            break
    return start, end


def _apply_selection(editor, value, add_blank=False):
    """Helper function that does the modifications in the text buffer."""
    if add_blank:
        value = '%s ' % value
    buffer_ = editor.textview.buffer
    start, end = get_fragment_bounds(buffer_, replace_mode=True, value=value)
    buffer_.begin_user_action()
    buffer_.delete(start, end)
    buffer_.insert(start, value)
    buffer_.end_user_action()

# ----
# Callbacks
# ----

def editor_key_pressed(textview, event, editor, window):
    """Handle editor's key-press-event when popup is visible."""
    if event.keyval == gtk.keysyms.Escape:
        destroy_popup(textview, window)
        textview.stop_emission('key-press-event')
        return True
    elif event.keyval == gtk.keysyms.Down:
        select_offset(window, 1)
        textview.stop_emission('key-press-event')
        return True
    elif event.keyval == gtk.keysyms.Up:
        select_offset(window, -1)
        textview.stop_emission('key-press-event')
        return True
    elif event.keyval == gtk.keysyms.Page_Down:
        select_offset(window, 5)
        textview.stop_emission('key-press-event')
        return True
    elif event.keyval == gtk.keysyms.Page_Up:
        select_offset(window, -5)
        textview.stop_emission('key-press-event')
        return True
    elif event.keyval == gtk.keysyms.Return:
        apply_selection(window, editor)
        textview.stop_emission('key-press-event')
        return True
    gobject.idle_add(editor_autocomplete, editor, window)
    return False


def on_editor_key_pressed_tab(sqlview, event, editor):
    """Tab key was pressed. Should only occur in advanced mode."""
    if event.keyval != gtk.keysyms.Tab:
        return False
    editor_autocomplete_advanced(editor)
    return True


def on_editor_created(instance, editor):
    """Connects to key-press-event to track TABs in advanced mode."""
    if instance.app.config.get('editor.tabcompletion'):
        if editor.get_data('cf::ac_tab') is not None:  # already connected
            return
        sig = editor.textview.connect('key-press-event',
                                      on_editor_key_pressed_tab, editor)
        editor.set_data('cf::ac_tab', sig)


def on_config_changed(config, key, enabled):
    """Tracks changes of editor.tabcompletion."""
    if key == 'editor.tabcompletion':
        for instance in config.app.get_instances():
            for editor in instance.get_editors():
                if enabled:
                    on_editor_created(instance, editor)
                elif not enabled and editor.get_data('cf::ac_tab'):
                    editor.textview.disconnect(editor.get_data('cf::ac_tab'))
                    editor.set_data('cf::ac_tab', None)


UI = """<menubar name="MenuBar">
  <menu name="Query" action="query-menu-action">
    <placeholder name="query-extensions">
      <menuitem name="query-autocomplete" action="query-autocomplete" />
    </placeholder>
  </menu>
</menubar>"""
