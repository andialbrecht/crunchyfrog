# -*- coding: utf-8 -*-

import os
import tempfile

from utils import InstanceTest

from cf.ui.confirmsave import ConfirmSaveDialog


ConfirmSaveDialog.run = lambda s: s._test_response


class TestConfirmSave(InstanceTest):

    def setUp(self):
        super(TestConfirmSave, self).setUp()
        _, self.fname1 = tempfile.mkstemp()
        _, self.fname2 = tempfile.mkstemp()

    def tearDown(self):
        os.remove(self.fname1)
        os.remove(self.fname2)
        super(TestConfirmSave, self).tearDown()

    def test_single(self):
        editor = self.instance.editor_create()
        editor.set_text('foo')
        ConfirmSaveDialog._test_response = 0  # cancel
        editor.close()
        self.assert_(editor in self.instance._editors)
        ConfirmSaveDialog._test_response = 2  # close without saving
        editor.close()
        self.assertEqual(self.instance._editors, [])

    def test_file_single(self):
        f = open(self.fname1, 'w')
        f.write('foo')
        f.close()
        editor = self.instance.editor_create(fname=self.fname1)
        editor.set_text('foo bar')
        ConfirmSaveDialog._test_response = 0  # cancel
        editor.close()
        self.assertEqual(open(self.fname1).read(), 'foo')
        ConfirmSaveDialog._test_response = 1  # save
        editor.close()
        self.assertEqual(open(self.fname1).read(), 'foo bar')

    def test_file_multiple(self):
        f = open(self.fname1, 'w')
        f.write('foo')
        f.close()
        f = open(self.fname2, 'w')
        f.write('bar')
        f.close()
        editor = self.instance.editor_create(fname=self.fname1)
        editor.set_text('foo bar')
        editor = self.instance.editor_create(fname=self.fname2)
        editor.set_text('bar bar')
        ConfirmSaveDialog._test_response = 0  # cancel
        self.instance.close_all_editors()
        self.assertEqual(open(self.fname1).read(), 'foo')
        self.assertEqual(open(self.fname2).read(), 'bar')
        ConfirmSaveDialog._test_response = 1  # save
        self.instance.close_all_editors()
        self.assertEqual(open(self.fname1).read(), 'foo bar')
        self.assertEqual(open(self.fname2).read(), 'bar bar')
