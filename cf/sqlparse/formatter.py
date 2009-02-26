# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""SQL formatter"""

import logging

import filters
from lexer import Lexer


def format(statement, **options):
    logging.info('OPTIONS %r', options)
    lexer = Lexer()
    lexer.add_filter(filters.IfFilter())
#    lexer.add_filter('whitespace')
    lexer.add_filter(filters.GroupFilter())
    if options.get('reindent', False):
        lexer.add_filter(filters.StripWhitespaceFilter())
        lexer.add_filter(filters.IndentFilter(
            n_indents=options.get('n_indents', 2)))
    if options.get('ltrim', False):
        lexer.add_filter(filters.LTrimFilter())
    keyword_case = options.get('keyword_case', None)
    if keyword_case is not None:
        assert keyword_case in ('lower', 'upper', 'capitalize')
        lexer.add_filter(filters.KeywordCaseFilter(case=keyword_case))
    identifier_case = options.get('identifier_case', None)
    if identifier_case is not None:
        assert identifier_case in ('lower', 'upper', 'capitalize')
        lexer.add_filter(filters.IdentifierCaseFilter(case=identifier_case))
    if options.get('strip_comments', False):
        lexer.add_filter(filters.StripCommentsFilter())
    right_margin = options.get('right_margin', None)
    if right_margin is not None:
        right_margin = int(right_margin)
        assert right_margin > 0
        lexer.add_filter(filters.RightMarginFilter(margin=right_margin))
    lexer.add_filter(filters.UngroupFilter())
    if options.get('output_format', None):
        ofrmt = options['output_format']
        assert ofrmt in ('sql', 'python', 'php')
        if ofrmt == 'python':
            lexer.add_filter(filters.OutputPythonFilter())
        elif ofrmt == 'php':
            lexer.add_filter(filters.OutputPHPFilter())
    tokens = []
    for ttype, value in lexer.get_tokens(unicode(statement)):
        tokens.append((ttype, value))
    return statement.__class__(tokens)
