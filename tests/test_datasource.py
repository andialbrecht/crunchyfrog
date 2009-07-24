import unittest

from tests.utils import AppTest

from cf.db import Datasource, Connection, Query
from cf.db.url import URL
from cf import sqlparse


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

    def test_execute_emit(self):
        self.res_q = None
        def _check_cb(datasource, q):
            self.res_q = q
        sql1 = 'create table foo (val integer);'
        conn = self.ds.dbconnect()
        query = Query(sql1, conn)
        self.assertEmitted((self.ds, 'executed', _check_cb),
                           query.execute)
        self.assert_(isinstance(self.res_q, Query),
                     'Expected Query, got %r' % self.res_q)

