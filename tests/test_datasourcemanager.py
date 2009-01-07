# -*- coding: utf-8 -*-

import os

from cf.datasources import DatasourceError

from utils import AppTest


class TestDatasourceManager(AppTest):

    def test_appattribute(self):
        self.assert_(hasattr(self.app, 'datasources'))
        self.assert_(self.app.datasources)

    def test_createds(self):
        initial = {'password': 'foo', 'user': 'bar',
                   'host': 'example.com', 'port': 1234,
                   'description': 'Dummy data source'}
        self.assertRaises(DatasourceError,
                          self.app.datasources.create,
                          None, None, **initial)
        ds = self.app.datasources.create('test', 'sqlite', **initial)
        self.assertRaises(DatasourceError,
                          self.app.datasources.create,
                          'test', 'sqlite', **initial)

    def test_writeconfig(self):
        self.app.datasources.write_dsconfig()
        self.assert_(os.path.isfile(self.app.datasources.dsconfig_file))
