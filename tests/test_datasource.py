import unittest

from tests.utils import AppTest

from cf.db import Datasource, Connection
from cf.db.url import URL


class TestDatasource(AppTest):

    def setUp(self):
        super(TestDatasource, self).setUp()
        self.ds = Datasource(self.app.datasources)
        self.ds.url = URL('sqlite', database=':memory:')

    def test_open_close_connection(self):
        conn = self.ds.dbconnect()
        self.assert_(isinstance(conn, Connection),
                     'dbconnect returned %r, expected Connection' % conn)
        self.assertEqual(len(self.ds.connections), 1)
        self.assertEqual(self.ds.connections, set([conn]))
        self.assertEmitted((conn, 'closed'), conn.close)
        self.assertEqual(len(self.ds.connections), 0)
        self.assertEqual(self.ds.connections, set([]))
