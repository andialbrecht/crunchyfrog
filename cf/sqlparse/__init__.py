# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""Parse SQL statements."""

import logging
import os

# Setup namespace
from errors import SQLParseError
from errors import SQLParseParseError
from errors import SQLParseMultiStatementError
from query import Query

import tokenizer as _tokenizer
from dialects import DialectDefault, DialectPSQL
_default_dialect = DialectDefault()


if 'SQLPARSE_DEBUG' in os.environ:
    logging.basicConfig(level=logging.DEBUG)


def sqlparse(statement, dialect=None):
    """Parse a SQL statement.

    Args:
        statement: String containing a SQL statement.

    Returns:
        A Query object.

    Raises:
        SQLParseParseError if parsing fails.
        SQLParseMultiStatementError if statement has more than one statement.
    """
    if dialect is None:
        dialect = _default_dialect
    return Query(statement, dialect)


def sqlsplit(statements, dialect=None):
    """Parse statements in a list of statements."""
    if dialect is None:
        dialect = _default_dialect
    splitted = _tokenizer._split_statements(_tokenizer._tokenize(statements,
                                                                 dialect),
                                            dialect)
    return [_tokenizer._join_tokens(tokens)
            for tokens in splitted]
