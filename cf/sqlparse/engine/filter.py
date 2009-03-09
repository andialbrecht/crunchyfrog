# -*- coding: utf-8 -*-

class TokenFilter(object):

    def __init__(self, **options):
        self.options = options

    def process(self, stack, stream):
        """Process token stream."""
        raise NotImplementedError
