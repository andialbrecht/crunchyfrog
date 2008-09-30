# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""This module contains the Query class."""

import logging

from dialects import DialectDefault, Dialect
from errors import SQLParseMultiStatementError
import tokenizer


class Query(object):
    """Interface to a SQL statement.

    The Query class is heavily inspired by the GQL class found in
    google.appengine.ext.gql package.
    """

    SELECT = 'SELECT'
    INSERT = 'INSERT'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    CREATE = 'CREATE'
    DROP = 'DROP'
    OTHER = 'OTHER'

    def __init__(self, statement, dialect=None):
        """Constructor.

        Args:
            statement: SQL statement as string.
            dialect: A Dialect instance.

        Raises:
            AssertionError if statement is not a string or unicode.
            SQLParseMultiStatementError if statement contains
                than one statement.
        """
        assert isinstance(statement, basestring)
        if dialect is None:
            dialect = DialectDefault()
        assert isinstance(dialect, Dialect)
        self._statement = statement
        self._dialect = dialect
        self._tokens = tokenizer._tokenize(statement, self._dialect)
        logging.debug('Query()._tokens --> %r', self._tokens)
        if tokenizer._is_multistatement(self._tokens, self._dialect):
            raise SQLParseMultiStatementError

    def __str__(self):
        return self.join()

    def __repr__(self):
        repr = self._statement[:10]
        if len(self._statement) > 10:
            repr += '...'
        return '<Query \'%s\'>' % repr

    def join(self):
        """Returns a string representation of the query."""
        return tokenizer._join_tokens(self._tokens)

    @property
    def tokens(self):
        return self._tokens

    @property
    def query_type(self):
        """Returns the type of the query.

        Returns:
            One of Query.SELECT, Query.INSERT, Query.UPDATE, Query.DELETE,
                Query.CREATE, Query.DROP, Query.OTHER.
        """
        for token in self._tokens:
            # Ignore trailing whitespaces.
            if token.type == token.WHITESPACE:
                continue
            token = token.upper()
            if token == 'SELECT':
                return Query.SELECT
            elif token == 'INSERT':
                return Query.INSERT
            elif token == 'UPDATE':
                return Query.UPDATE
            elif token == 'DELETE':
                return Query.DELETE
            elif token == 'CREATE':
                return Query.CREATE
            elif token == 'DROP':
                return Query.DROP
            else:
                return Query.OTHER

    def token_start(self):
        """Get the first token."""
        return self.tokens[0]

    def token_next(self, token):
        """Get the next token relative to token."""
        return token._next

    def token_prev(self, token):
        """Get the previous token relative to token."""
        return token._prev

    def token_end(self):
        """Get the last token."""
        return self.tokens[-1]

    def find_keyword(self, keyword, start=None, end=None):
        """Find a keyword token between start and end."""
        if start is None:
            start = self.token_start()
        if end is None:
            end = self.token_end()
        token = start
        while token:
            if token.type == token.KEYWORD \
            and token.upper() == keyword.upper():
                return token
            if token == end:
                break
            token = self.token_next(token)
        return None
