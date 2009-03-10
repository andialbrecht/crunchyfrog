# -*- coding: utf-8 -*-

import re

from sqlparse.engine import grouping
from sqlparse import tokens as T


class Filter(object):

    def process(self, *args):
        raise NotImplementedError


class TokenFilter(Filter):

    def process(self, stack, stream):
        raise NotImplementedError


def rstrip(stream):
    buff = []
    for token in stream:
        if token.is_whitespace() and '\n' in token.value:
            # assuming there's only one \n in value
            before, rest = token.value.split('\n', 1)
            token.value = '\n%s' % rest
            buff = []
            yield token
        elif token.is_whitespace():
            buff.append(token)
        elif token.is_group():
            token.tokens = list(rstrip(token.tokens))
            # process group and look if it starts with a nl
            if token.tokens and token.tokens[0].is_whitespace():
                before, rest = token.tokens[0].value.split('\n', 1)
                token.tokens[0].value = '\n%s' % rest
                buff = []
            while buff:
                yield buff.pop(0)
            yield token
        else:
            while buff:
                yield buff.pop(0)
            yield token


# --------------------------
# token process

class _CaseFilter(TokenFilter):

    ttype = None

    def __init__(self, case=None):
        if case is None:
            case = 'upper'
        assert case in ['lower', 'upper', 'capitalize']
        self.convert = getattr(unicode, case)

    def process(self, stack, stream):
        for ttype, value in stream:
            if ttype in self.ttype:
                value = self.convert(value)
            yield ttype, value


class KeywordCaseFilter(_CaseFilter):
    ttype = T.Keyword


class IdentifierCaseFilter(_CaseFilter):
    ttype = (T.Name, T.String.Symbol)


# ----------------------
# statement process

class StripCommentsFilter(Filter):

    def _process(self, stream):
        token_before = None
        stripped_single = False
        for token in stream:
            if token.is_group():
                token.tokens = self._process(token.tokens)
            if isinstance(token, grouping.CommentMulti):
                continue
            elif token.ttype is T.Comment.Single:
                stripped_single = True
                continue
            if (stripped_single and not token_before.is_whitespace()
                and token.ttype is not T.Whitespace):
                yield grouping.Token(T.Whitespace, ' ')
            if not token.is_whitespace():
                stripped_single = False
            yield token
            token_before = token

    def process(self, stack, group):
        group.tokens = self._process(group.tokens)


class StripWhitespaceFilter(Filter):

    def _handle_group(self, stmt, group):
        def streamer(s, stream):
            for item in stream:
                yield item
        func_name = '_group_%s' % group.__class__.__name__.lower()
        func = getattr(self, func_name, streamer)
        return func(stmt, group.tokens)

    def _group_comment(self, stmt, stream):
        # Comments have trainling whitespaces. So yield either nothing
        # or a new line afterwards.
        yield_new_line = False
        for token in stream:
            if token.is_whitespace():
                if value == '\n':
                    yield_new_line = True
            elif token.is_group():
                token.tokens = self._handle_group(stmt, token)
                yield token
            else:
                yield token
        if yield_new_line:
            yield grouping.Token(T.Whitespace, '\n')

    def _group_parenthesis(self, stmt, stream):
        at_start = False
        buffered_ws = []
        for token in stream:
            if token.match(T.Punctuation, '('):
                at_start = True
                yield token
            elif at_start:
                if token.is_whitespace():
                    continue
                at_start = False
                yield token
            elif token.is_whitespace():
                buffered_ws.append(token)
            else:
                if not token.match(T.Punctuation, ')') and buffered_ws:
                    yield grouping.Token(T.Whitespace, ' ')
                    buffered_ws = []
                yield token

    def _process(self, stack, stmt):
        buffered_ws = []
        for token in stmt.tokens:
            if token.is_whitespace():
                token.value = re.sub('[ \t\n]+', ' ', token.value)
                buffered_ws.append(token)
            elif token.is_group():
                for item in buffered_ws:
                    yield item
                buffered_ws = []
                token.tokens = self._handle_group(stmt, token)
                yield token
            else:
                for item in buffered_ws:
                    yield item
                buffered_ws = []
                yield token


    def process(self, stack, stmt):
        # TODO(andi): Somehow here's a problem with nested generators
        stmt.tokens = tuple(self._process(stack, stmt))
        for subgroup in stmt.subgroups:
            self.process(stack, subgroup)


class ReindentFilter(Filter):

    indents = {
        'FROM': 0,
        'JOIN': 0,
        'WHERE': 0,
        'AND': 0,
        'OR': 0,
        'GROUP': 0,
        'ORDER': 0,
        'UNION': 0,
        'SELECT': 0,
    }

    keep_together = (
        grouping.TypeCast, grouping.Identifier, grouping.Alias,
    )

    def __init__(self, width=2, char=' '):
        self.width = width
        self.char = char
        self._last_stmt = None
        self.nl_yielded = False
        self.level = 0
        self.line_offset = 0
        self._indent = []  # if set it's used for nl()

    def nl(self):
        """Build newline and leading whitespace. Calculate new line_offset."""
        if not self._indent:
            width = (len(self.char)*self.width)*self.level
            indent = ((self.char*self.width)*self.level)
        else:
            indent = self.char*self._indent[-1]
            width = len(self.char)*self._indent[-1]
        self.line_offset = width
        return '\n'+indent

    def _process_group(self, stmt, group):
        def _default(x, y):
            for item in self._process(None, x, y):
                yield item
        func_name = '_group_%s' % group.__class__.__name__.lower()
        func = getattr(self, func_name, _default)
        group.tokens = tuple(func(stmt, group.tokens))
        return group

    def _group_parenthesis(self, stmt, stream):
        def start_on_nl(stream):
            """Checks, if the opening parenthesis should be on a new line.
            That is when the parenthesis if followed by an DML keyword.
            """
            for token in stream:
                if token.ttype is T.Keyword.DML:
                    return True
                elif token.match(T.Punctuation, '('):
                    continue
                elif token.is_whitespace():
                    continue
                else:
                    return False
            return False

        lvl_changed = False
        start_on_nl = start_on_nl(stream)
        if start_on_nl:
            self.level += 1
            lvl_changed = True
            # FIXME(andi): The nl should be injected into the parent stream.
            yield grouping.Token(T.Whitespace, self.nl())
        offset = self.line_offset+1
        buff = []
        for token in stream:
            self._indent.append(offset)
            if token.match(T.Punctuation, ')'):
                for item in self._process(None, stmt, buff):
                    yield item
                buff = []
                yield token
            elif token.is_group():
#                self._process_group(stmt, token)
                buff.append(token)
            elif start_on_nl and len(buff) == 0:  # prevent nl before DDL/DML
                if (token.ttype in (T.Keyword.DML, T.Keyword.DDL)
                    or token.match(T.Punctuation, '(')):
                    yield token
                else:
                    buff.append(token)
            else:
                buff.append(token)
            self._indent.pop()
        for item in buff:
            yield item
        if buff and self._indent:
            self._indent.pop()
        if lvl_changed:
            self.level -= 1

    def _group_where(self, stmt, stream):
        lvl_changed = False
        yield grouping.Token(T.Whitespace, self.nl())
        for token in stream:
            if token.match(T.Keyword, ('AND', 'OR')):
                if not lvl_changed:
                    self.level += 1
                    lvl_changed = True
                yield grouping.Token(T.Whitespace, self.nl())
            elif token.is_group():
                token = self._process_group(stmt, token)
            if not token.is_group():
                self.line_offset += len(token.value)
            yield token
        if lvl_changed:
            self.level -= 1

    def _process(self, stack, stmt, stream):
        skip_ws = False
        if (self._last_stmt is not None and self._last_stmt != stmt
            and not self.nl_yielded):
            yield grouping.Token(T.Whitespace, self.nl())
            yield grouping.Token(T.Whitespace, self.nl())
        if self._last_stmt != stmt:
            self._last_stmt = stmt
            skip_ws = True
        is_first = True
        for token in stream:
            if skip_ws and token.is_whitespace():
                continue
            elif skip_ws and token.ttype is T.Comment.Single:
                self.nl_yielded = True
                yield token
                continue  # ends with a new line
            skip_ws = False
            if token.match(T.Keyword, list(self.indents)):
                yield grouping.Token(T.Whitespace, self.nl())
                self.level += self.indents[token.value.upper()]
                self.line_offset += len(token.value)
                yield token
            elif token.ttype is T.Keyword and 'JOIN' in token.value.upper():
                yield grouping.Token(T.Whitespace, self.nl())
                self.line_offset += len(token.value)
                yield token
            elif (token.ttype in (T.Keyword.DML, T.Keyword.DDL)
                  and not self.nl_yielded and not is_first):
                yield grouping.Token(T.Whitespace, self.nl())
                self.nl_yielded = True
                self.line_offset += len(token.value)
                yield token
            elif token.is_group():
                if not token.__class__ in self.keep_together:
                    self._process_group(stmt, token)
                yield token
            else:
                self.line_offset += len(token.value)
                self.nl_yielded = (token.match(T.Punctuation, '\n')
                                   or token.ttype is T.Comment.Single)
                yield token
            is_first = False

    def process(self, stack, group):
        group.tokens = rstrip(self._process(stack, group, group.tokens))


class RightMarginFilter(Filter):

    keep_together = (
        grouping.TypeCast, grouping.Identifier, grouping.Alias,
    )

    def __init__(self, width=79):
        self.width = width
        self.line = ''

    def _process(self, stack, group, stream):
        for token in stream:
            if token.is_whitespace() and '\n' in token.value:
                if token.value.endswith('\n'):
                    self.line = ''
                else:
                    self.line = token.value.splitlines()[-1]
            elif (token.is_group()
                  and not token.__class__ in self.keep_together):
                token.tokens = self._process(stack, token, token.tokens)
            else:
                val = token.to_unicode()
                if len(self.line) + len(val) > self.width:
                    match = re.search('^ +', self.line)
                    if match is not None:
                        indent = match.group()
                    else:
                        indent = ''
                    yield grouping.Token(T.Whitespace, '\n%s' % indent)
                    self.line = indent
                self.line += val
            yield token

    def process(self, stack, group):
        group.tokens = self._process(stack, group, group.tokens)


# ---------------------------
# postprocess

class SerializerUnicode(Filter):

    def process(self, stack, stmt):
        return stmt.to_unicode()


class OutputPythonFilter(Filter):

    def __init__(self, varname='sql'):
        self.varname = varname
        self.cnt = 0

    def _process(self, stream, varname, count, has_nl):
        if count > 1:
            yield grouping.Token(T.Whitespace, '\n')
        yield grouping.Token(T.Name, varname)
        yield grouping.Token(T.Whitespace, ' ')
        yield grouping.Token(T.Operator, '=')
        yield grouping.Token(T.Whitespace, ' ')
        if has_nl:
            yield grouping.Token(T.Operator, '(')
        yield grouping.Token(T.Text, "'")
        cnt = 0
        for token in stream:
            cnt += 1
            if token.is_whitespace() and '\n' in token.value:
                if cnt == 1:
                    continue
                after_lb = token.value.split('\n', 1)[1]
                yield grouping.Token(T.Text, "'")
                yield grouping.Token(T.Whitespace, '\n')
                for i in range(len(varname)+4):
                    yield grouping.Token(T.Whitespace, ' ')
                yield grouping.Token(T.Text, "'")
                if after_lb:  # it's the indendation
                    yield grouping.Token(T.Whitespace, after_lb)
                continue
            elif token.value and "'" in token.value:
                token.value = token.value.replace("'", "\\'")
            yield grouping.Token(T.Text, token.value or '')
        yield grouping.Token(T.Text, "'")
        if has_nl:
            yield grouping.Token(T.Operator, ')')

    def process(self, stack, stmt):
        self.cnt += 1
        if self.cnt > 1:
            varname = '%s%d' % (self.varname, self.cnt)
        else:
            varname = self.varname
        has_nl = len(stmt.to_unicode().strip().splitlines()) > 1
        stmt.tokens = self._process(stmt.tokens, varname, self.cnt, has_nl)
        return stmt


class OutputPHPFilter(Filter):

    def __init__(self, varname='sql'):
        self.varname = '$%s' % varname
        self.count = 0

    def _process(self, stream, varname):
        if self.count > 1:
            yield grouping.Token(T.Whitespace, '\n')
        yield grouping.Token(T.Name, varname)
        yield grouping.Token(T.Whitespace, ' ')
        yield grouping.Token(T.Operator, '=')
        yield grouping.Token(T.Whitespace, ' ')
        yield grouping.Token(T.Text, '"')
        cnt = 0
        for token in stream:
            if token.is_whitespace() and '\n' in token.value:
                cnt += 1
                if cnt == 1:
                    continue
                after_lb = token.value.split('\n', 1)[1]
                yield grouping.Token(T.Text, '"')
                yield grouping.Token(T.Operator, ';')
                yield grouping.Token(T.Whitespace, '\n')
                yield grouping.Token(T.Name, varname)
                yield grouping.Token(T.Whitespace, ' ')
                yield grouping.Token(T.Punctuation, '.')
                yield grouping.Token(T.Operator, '=')
                yield grouping.Token(T.Whitespace, ' ')
                yield grouping.Token(T.Text, '"')
                if after_lb:
                    yield grouping.Token(T.Text, after_lb)
                continue
            elif '"' in token.value:
                token.value = token.value.replace('"', '\\"')
            yield grouping.Token(T.Text, token.value)
        yield grouping.Token(T.Text, '"')
        yield grouping.Token(T.Punctuation, ';')

    def process(self, stack, stmt):
        self.count += 1
        if self.count > 1:
            varname = '%s%d' % (self.varname, self.count)
        else:
            varname = self.varname
        stmt.tokens = tuple(self._process(stmt.tokens, varname))
        return stmt

