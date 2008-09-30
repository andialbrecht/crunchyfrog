# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""Statement tokenizer."""

import logging
import re


def _tokenize(statement, dialect):
    """Tokenize a SQL statement.

    Args:
        statement: SQL statement as string.
        dialect: A Dialect instance.

    Returns:
        List of tokens.
    """
    prev = None
    tokens = []
    for match in dialect.tokenizer_regex.finditer(statement):
        if match.start() != match.end():
            token =Token(statement[match.start():match.end()], dialect)
            if prev:
                prev._next = token
            token._prev = prev
            tokens.append(token)
            prev = token
    return tokens


def _join_tokens(tokens):
    """Reverse _tokenize()."""
    return ''.join(str(x) for x in tokens)


def _split_statements(tokens, dialect):
    """Split list of tokens into statements.

    Args:
        tokens: Tokens
        dialect: A Dialect instance.

    Returns:
        tuple where each element is a list of tokens for a statement.
    """
    statements = []
    statement = []
    statement_finished = False
    semicolon_split_level = 0
    for token in tokens:
        statement.append(token)
        semicolon_split_level += dialect.semicolon_split_level(token.upper())
        if token.type == token.SEMICOLON and not semicolon_split_level:
            statement_finished = True
            continue
        if statement_finished:
            new_token = statement.pop()
            statements.append(statement)
            statement = [new_token]
            statement_finished = False
    if statement:
        statements.append(statement)
    statements = tuple(statements)
    logging.debug('_split_statements() --> %r', statements)
    return statements


def _is_multistatement(tokens, dialect):
    """Returns True if tokens contains more than one statement.

    Args:
        tokens: Token list.
        dialect: A Dialect instance.
    """
    return len(_split_statements(tokens, dialect)) > 1


class Token(object):
    """Represents a token."""

    UNKNOWN = 0
    SEMICOLON = 1
    WHITESPACE = 2
    OPERATOR = 3

    def __init__(self, raw, dialect):
        """Constructor.

        Args:
          raw: The 'raw' token.
          dialect: The dialect used.
        """
        self._next = None
        self._prev = None
        self._raw = raw
        self._dialect = dialect

    def __str__(self):
        return str(self._raw)

    def __unicode__(self):
        return unicode(self._raw)

    @property
    def raw(self):
        return self._raw

    @property
    def type(self):
        if self._raw == ';':
            return self.SEMICOLON
        elif re.compile(r'\s+$').match(self._raw):
            return self.WHITESPACE
        elif self.upper() in self._dialect.operators:
            return self.OPERATOR
        else:
            return self.UNKNOWN

    def upper(self):
        return self._raw.upper()

