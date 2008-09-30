# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""Exceptions raised by sqlparse."""


class SQLParseError(Exception):
    """Base error for all errors in this module."""


class SQLParseParseError(SQLParseError):
    """Raised when SQL parsing fails."""


class SQLParseMultiStatementError(SQLParseError):
    """Raised when sqlparse() is called with a multi-statement string."""
