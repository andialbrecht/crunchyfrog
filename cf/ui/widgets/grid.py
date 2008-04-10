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

"""A grid view"""

# NOTE:
#     This module should have no cf dependencies!

import gtk
import gobject
import pango
import gnomevfs

import sys
import os

from gettext import gettext as _

GRID_LABEL_MAX_LENGTH = 100

class Grid(gtk.TreeView):
    """Data grid
    
    The view component of the grid.
    
    Signals
    =======
    
        selection-changed
            ``def callback(grid, selected_cells, user_param1, ...)``
            
            Emitted when selected cells have changed
            
    
    Selection
    =========
    
    This grid allows three different selections which exclude each
    other:
    
        * one or more columns (select all means all columns are selected)
        * a single cell
        * one or more rows
        
    Columns can be selected by clicking on the column header. A click on the
    header of the first column selects or de-selects all data. Rows can be
    selected by clicking on the first column of a row. Individual cells can
    be selected by clicking on that cell.
    """
    
    __gsignals__ = {
        "selection-changed" : (gobject.SIGNAL_RUN_LAST,
                               gobject.TYPE_NONE,
                               (gobject.TYPE_PYOBJECT,)),
    }
    
    def __init__(self):
        gtk.TreeView.__init__(self)
        self.description = None
        self.set_rules_hint(True)
        self.get_selection().set_mode(gtk.SELECTION_NONE)
        self.selected_columns = list()
        self.selected_rows = list()
        self.connect("button-press-event", self.on_button_pressed)
        
    def _setup_columns(self, rows):
        renderer = gtk.CellRendererText()
        renderer.set_property("background", self.get_style().dark[gtk.STATE_ACTIVE].to_string())
        renderer.set_property("alignment", pango.ALIGN_CENTER)
        renderer.set_property("xalign", 0)
        renderer.set_property("yalign", 0)
        renderer.set_property("width-chars", len(str(len(rows))))
        col = gtk.TreeViewColumn("#", renderer,
                                 text=(len(self.description)*4)+1
                                 )
        col.connect("clicked", self.on_first_header_clicked)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        col.set_resizable(True)
        col.set_min_width(50)
        col.set_data("pressed", False)
        self.append_column(col)
        offset_fg = len(self.description)*2
        offset_bg = len(self.description)*3
        for i in range(len(self.description)):
            item = self.description[i]
            renderer = gtk.CellRendererText()
            renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
            lbl = "%s" % (item[0].replace("_", "__"),)
            col = gtk.TreeViewColumn(lbl, renderer,
                                     markup=i, 
                                     foreground_gdk=offset_fg+i,
                                     background_gdk=offset_bg+i)
            col.connect("clicked", self.on_column_header_clicked)
            col.set_resizable(True)
            col.set_min_width(75)
            col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.append_column(col)
        self.set_headers_clickable(True)
        self.set_fixed_height_mode(True)
        
    def _setup_model(self, rows, description, coding_hint):
        model = GridModel(rows, description, self.get_style(),
                          coding_hint=coding_hint)
        old_model = self.get_model()
        if old_model:
            del old_model
        self.set_model(model)
        
    def _get_popup_for_cell(self, row, col):
        col = self.get_model_index(col)
        model = self.get_model()
        data = model.on_get_value(row, col+len(self.description)-1)
        popup = gtk.Menu()
        if data != None:
            if not isinstance(data, buffer):
                item = gtk.MenuItem(_(u"Copy value to clipboard"))
                item.connect("activate", self.on_copy_value_to_clipboard, data)
                item.show()
                popup.append(item)
                sep = gtk.SeparatorMenuItem()
                sep.show()
                popup.append(sep)
            if isinstance(data, buffer):
                mime = gnomevfs.get_mime_type_for_data(data)
                item = gtk.MenuItem(_(u"Save as..."))
                item.connect("activate", self.on_save_blob, data, mime)
                item.show()
                popup.append(item)
                if mime:
                    apps = gnomevfs.mime_get_all_applications(mime)
                    if apps:
                        item = gtk.MenuItem(_(u"Open with..."))
                        smenu = gtk.Menu()
                        item.set_submenu(smenu)
                        item.show()
                        popup.append(item)
                        for app_info in apps:
                            item = gtk.MenuItem(app_info[1])
                            item.connect("activate", self.on_open_blob, data, app_info)
                            item.show()
                            smenu.append(item)
            else:
                item = gtk.MenuItem(_(u"View value"))
                item.connect("activate", self.on_view_data, data)
                item.show()
                popup.append(item)
        else:
            item = gtk.MenuItem(_(u"This cell contains a 'NULL' value."))
            item.set_sensitive(False)
            item.show()
            popup.append(item)
        return popup
        
    def on_button_pressed(self, treeview, event):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                if col == self.get_columns()[0]:
                    return
                col = self.get_model_index(col)
                model = self.get_model()
                data = model.on_get_value(path[0], col+len(self.description)-1)
                if data == None:
                    return
                if not isinstance(data, buffer):
                    self.on_view_data(None, data)
        
        elif event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                if col == self.get_columns()[0]:
                    return
                self.select_cell(path[0], col, not self.cell_is_selected(path[0], col))
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                popup = self._get_popup_for_cell(path[0], col)
                if not popup:
                    return
                popup.popup( None, None, None, event.button, time)
        
        elif event.button == 1:
            x = int(event.x)
            y = int(event.y)
            pthinfo = treeview.get_path_at_pos(x, y)
            if not pthinfo:
                return
            path, col, cellx, celly = pthinfo
            if col == self.get_columns()[0]:
                self.select_row(path[0], not self.row_is_selected(path[0]))
            else:
                self.select_cell(path[0], col, not self.cell_is_selected(path[0], col))
                
        
            
    def on_column_header_clicked(self, column):
        selected = not column in self.get_selected_columns()
        self.select_column(column, selected)
        
    def on_copy_value_to_clipboard(self, menuitem, value):
        display = gtk.gdk.display_manager_get().get_default_display()
        clipboard = gtk.Clipboard(display, "CLIPBOARD")
        clipboard.set_text(str(value))
        
    def on_first_header_clicked(self, column):
        selected = not column.get_data("pressed")
        for xcolumn in self.get_columns()[1:]:
            self.select_column(xcolumn, selected)
        column.set_data("pressed", selected)
        
    def on_open_blob(self, menuitem, data, app_info):
        fname = os.path.expanduser("~/cf-blob.file")
        cmd = "%s %s" % (app_info[2], fname)
        f = open(fname, "w")
        f.write(str(data))
        f.close()
        os.system(cmd)
        
    def on_save_blob(self, menuitem, data, mime):
        dlg = gtk.FileChooserDialog(_(u"Save as..."),
                                    None,
                                    gtk.FILE_CHOOSER_ACTION_SAVE,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                     gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        if mime:
            filter = gtk.FileFilter()
            filter.set_name(mime)
            filter.add_mime_type(mime)
            dlg.add_filter(filter)
            dlg.set_filter(filter)
            filter = gtk.FileFilter()
            filter.set_name(_(u"All files"))
            filter.add_pattern("*")
            dlg.add_filter(filter)
        if dlg.run() == gtk.RESPONSE_OK:
            f = open(dlg.get_filename(), "w")
            f.write(str(data))
            f.close()
        dlg.destroy()
        
    def on_view_data(self, menuitem, data):
        dlg = DataViewer(data)
        dlg.run()
        dlg.destroy()
        
    def cell_is_selected(self, row, column):
        """Returns ``True`` is a cell is selected
        
        :Parameter:
            row
                Row number
            column
                ``gtk.TreeViewColumn``
        """
        col = self.get_model_index(column)-1
        return (row, col) in self.get_model().selected_cells
    
    def get_cell_data(self, cell, repr=False):
        """Returns the content of a cell
        
        :Parameter:
            cell
                A row-cell tuple
            repr
                If ``True`` the content of the cell is returned as text (default: ``False``)
        :Returns: Cell content
        """
        model = self.get_model()
        data = model.on_get_value(cell[0], cell[1]+len(self.description))
        if repr:
            data = model._get_markup_for_value(data, strip_length=False, markup=False)
        return data
    
    def get_grid_data(self):
        """Returns all data"""
        return self.get_model().rows
    
    def get_model_index(self, treeview_column):
        """Returns the model index for a column
        
        :Parameter:
            treeview_column
                ``gtk.TreeViewColumn`
        
        .. Note:: 
            This method returns the label column.
        """
        columns = self.get_columns()
        for i in range(len(columns)):
            if columns[i] == treeview_column:
                return i
            
    def get_selected_cells(self):
        """Returns selected cells"""
        return self.get_model().selected_cells
    
    def get_selected_columns(self):
        """Returns selected columns"""
        return self.selected_columns
    
    def get_selected_rows(self):
        """Returns selected rows"""
        return self.selected_rows
        
    def reset(self):
        """Resets the grid"""
        old_model = self.get_model()
        if old_model:
            del old_model
        model = gtk.ListStore(int)
        self.set_model(model)
        while self.get_columns():
            col = self.get_column(0)
            self.remove_column(col)
            
    def row_is_selected(self, row):
        """Returns ``True`` if the row is selected
        
        :Parameter:
            row
                Row number
        """
        return row in self.selected_rows
    
    def select_cell(self, row, column, selected):
        """Selects a cell
        
        :Parameter:
            row
                A row index
            column
                A ``gtk.TreeViewColumn``
            selected
                ``True`` if the cell should be selected
        """
        col = self.get_model_index(column)-1
        path = (row, col)
        model = self.get_model()
        self.unselect_cells()
        if selected:
            self.unselect_rows()
            self.unselect_columns()
        if selected and path not in model.selected_cells:
            model.selected_cells.append(path)
        elif not selected and path in model.selected_cells:
            model.selected_cells.remove(path)
        self.emit("selection-changed", model.selected_cells)
            
    def select_column(self, column, selected):
        """Selects a column
        
        :Parameter:
            column
                a ``gtk.TreeViewColumn``
            selected
                ``True`` if the column should be selected
        """
        if column in self.get_selected_columns() \
        and not selected:
            style = self.get_style().bg[gtk.STATE_NORMAL]
            background_set = False
            self.selected_columns.remove(column)
        elif column not in self.get_selected_columns() \
        and selected:
            style = self.get_style().bg[gtk.STATE_SELECTED]
            background_set = True
            self.unselect_rows()
            self.unselect_cells()
            self.selected_columns.append(column)
        else:
            return
        for renderer in column.get_cell_renderers():
            renderer.set_property("cell-background-gdk", style)
            renderer.set_property("cell-background-set", background_set)
        # rebuild selected_cells
        self.unselect_cells()
        model = self.get_model()
        for i in range(len(model.rows)):
            for column in self.get_selected_columns():
                j = self.get_model_index(column)-1
                model.selected_cells.append((i, j))
        self.queue_draw()
        self.emit("selection-changed", model.selected_cells)
        
    def select_row(self, row, selected):
        """Selects a row
        
        :Parameter:
            row
                the row number
            selected
                ``True`` if the row should be selected
        """
        if selected and not self.row_is_selected(row):
            self.unselect_columns()
            if not self.selected_rows:
                self.unselect_cells()
            self.selected_rows.append(row)
            model = self.get_model()
            for i in range(len(self.get_columns())):
                path = (row, i)
                model.selected_cells.append(path)
        elif not selected and self.row_is_selected(row):
            self.selected_rows.remove(row)
            model = self.get_model()
            for i in range(len(self.get_columns())):
                path = (row, i)
                if path in model.selected_cells:
                    model.selected_cells.remove(path)
        else:
            return
        self.queue_draw()
        self.emit("selection-changed", model.selected_cells)
    
    def set_result(self, rows, description, coding_hint="utf-8"):
        """Sets the result and updates the grid
        
        :Parameter:
            rows
                Sequence of rows
            description
                DB-API2 like description
        """
        self.description = description
        self._setup_columns(rows)
        self._setup_model(rows, description, coding_hint)
        
    def unselect_cells(self):
        """Unselects all cells"""
        model = self.get_model()
        model.selected_cells = []
        
    def unselect_columns(self):
        """Unselects all columns"""
        while self.get_selected_columns():
            column = self.get_selected_columns()[0]
            self.select_column(column, False)
            
    def unselect_rows(self):
        """Unselect all rows"""
        while self.get_selected_rows():
            row = self.get_selected_rows()[0]
            self.select_row(row, False)
        
class GridModel(gtk.GenericTreeModel):
    """Data grid model
    
    The model stores it's data in a plain Python list. It provides
    three virtual columns for a displayed version of a value (limited
    to ``GRID_LABEL_MAX_LENGTH`` characters to increase perfomance),
    a foreground and a background color for selected cells.
    
    This class re-uses some code of the `Nicotine`_ project (`FastListModel`_)
    found via Google's Code Search.
    
    .. _Nicotine: http://nicotine-plus.sourceforge.net/
    .. _FastListModel: http://www.google.com/codesearch?hl=de&q=+lang:python+GenericTreeModel+show:VRnMlwyOXFM:6NW9oRiVVfg:ANlgLtp-rX8&sa=N&cd=20&ct=rc&cs_p=http://ftp.tr.freebsd.org/pub/FreeBSD/distfiles/nicotine%2B-1.2.6.tar.bz2&cs_f=nicotine%2B-1.2.6/pynicotine/gtkgui/utils.py#first
    """
    
    def __init__(self, rows, description, style, coding_hint="utf-8"):
        """
        The constructor takes three arguments:
        
        :Parameter:
            rows
                Data as a plain python list of rows
            description
                DB-API2 like description
            style
                ``gtk.Style`` instance
        """
        gtk.GenericTreeModel.__init__(self)
        self.rows = rows
        self.description = description
        self.style = style
        self.coding_hint = coding_hint
        self.selected_cells = list()
        
    def _get_markup_for_value(self, value, strip_length=True, markup=True):
        style = self.style
        if value == None: 
            if markup:
                value = '<span foreground="%s">&lt;NULL&gt;</span>' % style.dark[gtk.STATE_PRELIGHT].to_string()
            else:
                value = 'null'
        elif isinstance(value, buffer):
            if markup:
                value = '<span foreground="%s">&lt;LOB&gt;</span>' % style.dark[gtk.STATE_PRELIGHT].to_string()
            else:
                value = str(buffer)
        else:
            if isinstance(value, str):
                value = unicode(value, self.coding_hint)
            elif isinstance(value, unicode):
                pass
            else:
                value = unicode(value)
            value = value.splitlines()
            if value:
                if strip_length:
                    value = value[0][:GRID_LABEL_MAX_LENGTH]
                else:
                    value = "\n".join(value)
            else:
                value = ""
            value = gobject.markup_escape_text(value)
        return value

    def on_get_flags(self):
        '''returns the GtkTreeModelFlags for this particular type of model'''
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns(self):
        '''returns the number of columns in the model'''
        return len(self.description)*4+1

    def on_get_column_type(self, index):
        '''returns the type of a column in the model'''
        length = len(self.description)
        range_label = range(length)
        range_data = range(length, length*2)
        range_fg = range(length*2, length*3)
        range_bg = range(length*3, length*4)
        if index in range_label:
            return str
        elif index in range_data:
            return gobject.TYPE_PYOBJECT
        elif index == self.on_get_n_columns():
            return int
        elif (index in range_fg) or (index in range_bg):
            return gtk.gdk.Color
        else:
            raise RuntimeError, "Unexpected index"

    def on_get_path(self, iter):
        '''returns the tree path (a tuple of indices at the various
        levels) for a particular node.'''
        return (iter,)

    def on_get_iter(self, path):
        '''returns the node corresponding to the given path.  In our
        case, the node is the path'''
        if path[0] < len(self.rows):
            return path[0]
        else:
            return None

    def on_get_value(self, iter, column):
        '''returns the value stored in a particular column for the node'''
        length = len(self.description)
        range_label = range(length)
        range_data = range(length, length*2)
        range_fg = range(length*2, length*3)
        range_bg = range(length*3, length*4)
        if column in range_label:
            raw = self.rows[iter][column]
            markup = self._get_markup_for_value(raw)
            return markup
        elif column in range_data:
            return self.rows[iter][column-len(self.description)]
        elif column == self.on_get_n_columns():
            return iter+1
        elif column in range_fg:
            data_column = column-length*2
            if (iter, data_column) in self.selected_cells:
                return self.style.fg[gtk.STATE_SELECTED]
            else:
                return None
        elif column in range_bg:
            data_column = column-length*3
            if (iter, data_column) in self.selected_cells:
                return self.style.bg[gtk.STATE_SELECTED]
            else:
                return None
        else:
            raise RuntimeError, "Unexpected index %r" % column 

    def on_iter_next(self, iter):
        '''returns the next node at this level of the tree'''
        if iter + 1 < len(self.rows):
            return iter + 1
        else:
            return None

    def on_iter_children(self, iter):
        '''returns the first child of this node'''
        return 0

    def on_iter_has_child(self, iter):
        '''returns true if this node has children'''
        return False

    def on_iter_n_children(self, iter):
        '''returns the number of children of this node'''
        return len(self.rows)

    def on_iter_nth_child(self, iter, n):
        '''returns the nth child of this node'''
        return n

    def on_iter_parent(self, iter):
        '''returns the parent of this node'''
        return None
    
    
class DataViewer(gtk.Dialog):
    """Dialog to display a value"""
    
    def __init__(self, data):
        """
        The constructor of this class takes 1 argument:
        
        :Parameter:
            data
                A Python value to display
        """
        gtk.Dialog.__init__(self, _(u"Data"), None,
                            gtk.DIALOG_DESTROY_WITH_PARENT,
                            (gtk.STOCK_CLOSE, gtk.RESPONSE_OK))
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.vbox.pack_start(sw, True, True)
        tv = gtk.TextView()
        tv.set_editable(False)
        tv.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        tv.get_buffer().set_text(str(data))
        sw.add(tv)
        sw.show_all()
        self.resize(650, 550)
        
