# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""This module contains classes that represent SQL dialects."""

import re

_TOKENIZER_REGEX = r"""%(multiwordkeywords)s|
\s+|
;|
(?:'[^'\n\r]*')+|
<=|>=|!=|=|<|>|
:\w+|
,|
\*|
-?\d+(?:\.\d+)?|
\w+|
\(|\)|
\S+|
"""


class Dialect(object):

    operators = []

    def __init__(self):
        if hasattr(self, 'multi_word_keywords'):
            multiwordkeywords = '|'.join(self.multi_word_keywords)
        else:
            multiwordkeywords = ''
        regex = _TOKENIZER_REGEX % {'multiwordkeywords': multiwordkeywords}
        self._tokenizer_regex = re.compile(regex,
                                           re.VERBOSE | re.IGNORECASE)

    def semicolon_split_level(self, token):
        return 0

    @property
    def tokenizer_regex(self):
        return self._tokenizer_regex


class DialectDefault(Dialect):

    multi_word_keywords = [
        'END\sIF',
        'END\sLOOP',
    ]

    operators = [
        '=', '<', '>', '<=', '>=', 'IN'
    ]

    def __init__(self):
        super(DialectDefault, self).__init__()
        self._in_declare = False
        self._in_create = False

    def semicolon_split_level(self, token):
        """Returns a value to adjust the semicolon split level.

         0: Don't change level.
         1: Increase level.
        -1: Decrease level.

        For example, if token is 'BEGIN' 1 should be returned.
        """
        if token == 'DECLARE':
            self._in_declare = True
            return 1
        if token == 'CREATE':
            self._in_create = True
            return 1
        if token == 'BEGIN':
            if self._in_declare or not self._in_create:
                return 0
            return 1
        if token == 'END':
            return -1
        return 0

    def _get_operators(self):
        return super(DialectDefault, self)._get_operators()+self._operators


class DialectPSQL(DialectDefault):

    operators = DialectDefault.operators + [
        'LIKE', '~'
    ]

    def __init__(self):
        super(DialectPSQL, self).__init__()
        self._in_dbldollar = False

    def semicolon_split_level(self, token):
        if token == '$$':
            if not self._in_dbldollar:
                self._in_dbldollar = True
                return 1
            else:
                self._in_dbldollar = False
                return -1
        else:
            return super(DialectPSQL, self).semicolon_split_level(token)
