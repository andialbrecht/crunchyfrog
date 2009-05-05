# -*- coding: utf-8 -*-

"""Sphinx builder that generates docbook."""

import codecs
import sys
from os import path

from docutils import nodes, writers
from docutils.io import StringOutput

from sphinx.builder import TextBuilder
from sphinx.util import ensuredir, os_path
from sphinx.textwriter import TextTranslator

import docbook


class DocBookBuilder(TextBuilder):

    name = 'docbook'
    out_suffix = '.xml'

    XML_DECL = '<?xml version="1.0" encoding="%s"?>\n'

    DOCTYPE_DECL = """<!DOCTYPE %s
        PUBLIC "-//OASIS//DTD DocBook XML V4.2//EN"
        "http://www.oasis-open.org/docbook/xml/4.2/docbookx.dtd">\n"""

    def get_target_uri(self, docname, typ=None):
#        print >>sys.stderr, 'get_target_uri', docname, typ
       return './'+docname+self.out_suffix

    def prepare_writing(self, docnames):
        self.writer = DocBookWriter(self)

    def write_doc(self, docname, doctree):
        # Mostly copied from TextBuilder
        destination = StringOutput(encoding='utf-8')
        self.writer.write(doctree, destination)
        outfilename = path.join(self.outdir,
                                os_path(docname)+self.out_suffix)
        # normally different from self.outdir
        ensuredir(path.dirname(outfilename))
        try:
            f = codecs.open(outfilename, 'w', 'utf-8')
            try:
               f.write(''.join([self.XML_DECL % 'utf-8',
                                self.DOCTYPE_DECL % 'section'
                                ]+self.writer.output))
            finally:
                f.close()
        except (IOError, OSError), err:
            self.warn("Error writing file %s: %s" % (outfilename, err))


class DocBookWriter(docbook.Writer):
    supported = ('xml',)
    settings_defaults = {'doctype': 'artice'}
    settings_spec = (
        'DocBook-Specific Options',
        None,
        (('Set DocBook document type. '
            'Choices are "article", "book", and "chapter". '
            'Default is "article".',
            ['--doctype'],
            {'default': 'article', 
             'metavar': '<name>',
             'type': 'choice', 
             'choices': ('article', 'book', 'chapter',)
            }
         ),
        )
    )


    output = None

    def __init__(self, builder):
        docbook.Writer.__init__(self)
        self.builder = builder

    def translate(self):
        self.document.settings.doctype = 'article'
        visitor = DocBookTranslator(self.document, self.builder)
        self.document.walkabout(visitor)
        self.visitor = visitor
        self.output = visitor.body


class DocBookTranslator(docbook.DocBookTranslator):

    def __init__(self, document, builder):
        docbook.DocBookTranslator.__init__(self, document)

    def visit_target(self, node):
        pass

    def visit_compact_paragraph(self, node):
        pass
    def depart_compact_paragraph(self, node):
        pass

    def unknown_visit(self, node):
        raise NotImplementedError('Unknown node: ' + node.__class__.__name__)

def setup(app):
    app.add_builder(DocBookBuilder)
