# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""Parse SQL statements."""

import logging
import os


if 'SQLPARSE_DEBUG' in os.environ:
    logging.basicConfig(level=logging.DEBUG)


STATEMENT_TYPE_UNKNOWN = 0
STATEMENT_TYPE_SELECT = 1
STATEMENT_TYPE_INSERT = 2
STATEMENT_TYPE_DELETE = 3
STATEMENT_TYPE_UPDATE = 4
STATEMENT_TYPE_DROP = 5
STATEMENT_TYPE_CREATE = 6
STATEMENT_TYPE_ALTER = 7


# Setup namespace
from parser import Parser


def parse(sql, dialect=None):
    parser = Parser(dialect)
    return parser.parse(sql)


def split_str(sql, dialect=None):
    parser = Parser(dialect)
    return [unicode(statement) for statement in parser.parse(sql)]

sqlsplit = split_str
