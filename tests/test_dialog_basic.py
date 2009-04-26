# -*- coding: utf-8 -*-

"""Runs basic dialog tests."""

from utils import InstanceTest

from cf.ui.datasources import DatasourcesDialog
from cf.ui.prefs import PreferencesDialog


class TestDialogBasic(InstanceTest):

    def test_preferences(self):
        dlg = PreferencesDialog(self.instance)
        dlg.show_all()
        self.refresh_gui()
        self.assertEqual(dlg.widget.get_property('visible'), True)
        dlg.destroy()

    def test_datasources(self):
        dlg = DatasourcesDialog(self.app, self.instance)
        self.assertEqual(dlg.dlg.get_transient_for(), self.instance)
        dlg.dlg.show_all()
        self.refresh_gui()
        self.assertEqual(dlg.dlg.get_property('visible'), True)
        dlg.destroy()
