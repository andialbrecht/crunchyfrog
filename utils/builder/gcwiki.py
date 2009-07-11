# -*- coding: utf-8 -*-

"""Sphinx builder that generates wiki pages for Google Code."""

import codecs
import sys
from os import path

from docutils import nodes, writers
from docutils.io import StringOutput

from sphinx.builder import TextBuilder
from sphinx.util import ensuredir, os_path
from sphinx.textwriter import TextTranslator


class GCWikiBuilder(TextBuilder):

    name = 'gcwiki'
    out_suffix = '.wiki'

    def __init__(self, *args, **kwds):
        TextBuilder.__init__(self, *args, **kwds)
        self.sections = []

    def get_target_uri(self, docname, typ=None):
        return docname.capitalize()

    def prepare_writing(self, docnames):
        self.writer = GCWikiWriter(self)

    def write_doc(self, docname, doctree):
        # Mostly copied from TextBuilder
        destination = StringOutput(encoding='utf-8')
        self.writer.write(doctree, destination)
        outfilename = path.join(self.outdir,
                                os_path(docname.capitalize())+self.out_suffix)
        # normally different from self.outdir
        ensuredir(path.dirname(outfilename))
        try:
            f = codecs.open(outfilename, 'w', 'utf-8')
            try:
                f.write(self.writer.output)
            finally:
                f.close()
        except (IOError, OSError), err:
            self.warn("Error writing file %s: %s" % (outfilename, err))

    def finish(self):
        docname = 'Sidebar'
        outfilename = path.join(self.outdir,
                                os_path(docname.capitalize())+self.out_suffix)
        # normally different from self.outdir
        ensuredir(path.dirname(outfilename))
        sidebar = ''
        self.info('Writing sidebar')
        for level, node in self.sections:
            sidebar += '*%s %s %s\n' % (level, str(node.list_attributes), node.astext())
        try:
            f = codecs.open(outfilename, 'w', 'utf-8')
            try:
                f.write(sidebar)
            finally:
                f.close()
        except (IOError, OSError), err:
            self.warn("Error writing file %s: %s" % (outfilename, err))


class GCWikiWriter(writers.Writer):
    supported = ('text',)
    settings_spec = ('No options here.', '', ())
    settings_defaults = {}

    output = None

    def __init__(self, builder):
        writers.Writer.__init__(self)
        self.builder = builder

    def translate(self):
        visitor = GCWikiTranslator(self.document, self.builder)
        self.document.walkabout(visitor)
        self.output = visitor.body


class GCWikiTranslator(TextTranslator):

    def __init__(self, document, builder):
        TextTranslator.__init__(self, document, builder)
        self._builder = builder

#    def visit_target(self, node):
#        self.add_text('[%s ' % node.astext())
#    def depart_target(self, node):
#        self.add_text(']')

    def visit_section(self, node):
        self.sectionlevel += 1
        if self.sectionlevel > 6:
            self.sectionlevel = 6
        self._title_char = '='*self.sectionlevel
    def depart_section(self, node):
        self._title_char = ''
        self.sectionlevel -= 1

    def depart_title(self, node):
        if isinstance(node.parent, nodes.section):
            char = self._title_char
        else:
            char = '^'
        text = ''.join(x[1] for x in self.states.pop() if x[0] == -1)
        self.stateindent.pop()
        text = '%s %s %s' % ('='*self.sectionlevel, text,
                             '='*self.sectionlevel)
        self.states[-1].append((0, ['', text, '']))
        self._builder.sections.append((self.sectionlevel, node))

    def visit_emphasis(self, node):
        self.add_text('_')
    def depart_emphasis(self, node):
        self.add_text('_')

    def visit_literal_emphasis(self, node):
        self.add_text('_')
    def depart_literal_emphasis(self, node):
        self.add_text('_')

    def visit_strong(self, node):
        self.add_text('*')
    def depart_strong(self, node):
        self.add_text('*')

    def visit_title_reference(self, node):
        self.add_text('*')
    def depart_title_reference(self, node):
        self.add_text('*')

    def visit_literal(self, node):
        self.add_text('`')
    def depart_literal(self, node):
        self.add_text('`')

    def visit_subscript(self, node):
        self.add_text(',,sub,,')
    def depart_subscript(self, node):
        pass

    def visit_superscript(self, node):
        self.add_text('^super^')
    def depart_superscript(self, node):
        pass

    def visit_literal_block(self, node):
        self.new_state(0)
        self.add_text('{{{\n')
    def depart_literal_block(self, node):
        self.add_text('\n}}}')
        self.end_state(wrap=False)

    visit_doctest_block = visit_literal_block
    depart_doctest_block = depart_literal_block
    visit_line_block = visit_literal_block
    depart_line_block = depart_literal_block

    def visit_pending_xref(self, node):
        self.add_text('Pxref')
    def depart_pending_xref(self, node):
        pass

    def visit_reference(self, node):
        # attrs: ds, classes, names, dupnames, backrefs
        #self.add_text('%r' % repr(node.asdom().toxml()))
        if node.hasattr('refuri'):
            self.add_text('[%s ' % node['refuri'])
        else:
            self.add_text('NO REFURI')
    def depart_reference(self, node):
        self.add_text(']')


def setup(app):
    app.add_builder(GCWikiBuilder)
