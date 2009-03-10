# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""Parse SQL statements."""

__version__ = '0.1.0'

import logging
import os


if 'SQLPARSE_DEBUG' in os.environ:
    logging.basicConfig(level=logging.DEBUG)


class SQLParseError(Exception):
    """Base class for exceptions in this module."""


# Setup namespace
from sqlparse import engine
from sqlparse import filters
from sqlparse import formatter


def parse(sql):
    """Parse sql and return a list of statements.

    *sql* is a single string containting one or more SQL statements.

    The returned :class:`~sqlparse.parser.Statement` are fully analyzed.

    Returns a list of :class:`~sqlparse.parser.Statement` instances.
    """
    stack = engine.FilterStack()
    stack.full_analyze()
    return tuple(stack.run(sql))


def format(sql, **options):
    """Format *sql* according to *options*.

    Returns a list of :class:`~sqlparse.parse.Statement` instances like
    :meth:`parse`, but the statements are formatted according to *options*.

    Available options are documented in the :mod:`~sqlparse.format` module.
    """
    stack = engine.FilterStack()
    options = formatter.validate_options(options)
    stack = formatter.build_filter_stack(stack, options)
    stack.postprocess.append(filters.SerializerUnicode())
    return ''.join(stack.run(sql))


def split(sql):
    """Split *sql* into separate statements.

    Returns a list of strings.
    """
    stack = engine.FilterStack()
    stack.split_statements = True
    return [unicode(stmt) for stmt in stack.run(sql)]

