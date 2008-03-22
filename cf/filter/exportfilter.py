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
"""Export filter"""

from cf.plugins.core import ExportPlugin

from gettext import gettext as _

class CSVExportFilter(ExportPlugin):
    id = "crunchyfrog.export.csv"
    name = _(u"CSV Export")
    description = _(u"Export query results as CSV files")
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://cf.andialbrecht.de"
    version = "0.1"
    has_options = False
    
    file_filter_name = _(u"Text CSV (.csv)")
    file_filter_pattern = ["*.csv"]
    
    def __init__(self, app):
        ExportPlugin.__init__(self, app)
        
    def export(self, description, rows, options):
        import csv
        fp = open(options["filename"], "w")
        w = csv.writer(fp)
        w.writerows(rows)
        fp.close()
        
class OOCalcExportFilter(ExportPlugin):
    id = "crunchyfrog.export.odc"
    name = _(u"OpenDocument Export")
    description = _(u"Export query results as OpenDocument Spreadsheets")
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://cf.andialbrecht.de"
    version = "0.1"
    
    file_filter_name = _(u"OpenDocument Spreadsheet (.ods)")
    file_filter_pattern = ["*.ods"]
    
    def __init__(self, app):
        ExportPlugin.__init__(self, app)
        
    def export(self, description, rows, options):
        from cf.thirdparty import ooolib
        import pwd
        import os
        import types
        doc = ooolib.Calc()
        doc.set_meta('title', _(u"CrunchyFrog Data Export"))
        doc.set_meta('description', options.get("query", ""))
        doc.set_meta('creator', pwd.getpwuid(os.getuid())[4].split(",", 1)[0])
        doc.set_cell_property('bold', True)
        for i in range(len(description)):
            doc.set_cell_value(i+1, 1, "string", description[i][0])
        doc.set_cell_property('bold', False)
        for i in range(len(rows)):
            for j in range(len(rows[i])):
                value = rows[i][j]
                if value == None:
                    continue
                if type(value) == types.FloatType:
                    otype = "float" 
                elif type(value) == types.IntType:
                    otype = "int"
                elif type(value) == types.BooleanType:
                    otype = "boolean"
                else:
                    otype = "string"
                doc.set_cell_value(j+1, i+2, otype, value)
        doc.save(options["filename"])
            