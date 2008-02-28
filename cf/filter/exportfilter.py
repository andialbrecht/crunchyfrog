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
    name = _(u"CSV Export")
    description = _(u"Export query results as CSV files")
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://crunchyfrog.googlecode.com"
    version = "0.1"
    has_options = False
    
    file_filter_name = _(u"CSV file")
    file_filter_pattern = ["*.csv"]
    
    def __init__(self, app):
        ExportPlugin.__init__(self, app)
        
    def export(self, description, rows, options):
        import csv
        fp = open(options["filename"], "w")
        w = csv.writer(fp)
        w.writerows(rows)
        fp.close()
        
class XMLExportFilter(ExportPlugin):
    name = _(u"XML Export")
    description = _(u"Export query results as XML files")
    author = "Andi Albrecht"
    license = "GPL"
    homepage = "http://crunchyfrog.googlecode.com"
    version = "0.1"
    
    file_filter_name = _(u"XML file")
    file_filter_pattern = ["*.xml"]
    
    def __init__(self, app):
        ExportPlugin.__init__(self, app)