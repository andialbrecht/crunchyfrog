import unittest

from tests.utils import AppTest

from cf.db import Datasource, Connection
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
        return True  # FIXME: Test needs to be rewritten.
        def _check_cb(datasource, c, parsed):
            self.assert_(isinstance(parsed, sqlparse.sql.Statement),
                         'Expected sqlparse.sql.Statement, got %r' % parsed)
            self.assertEqual(unicode(parsed), sql1)
        sql1 = 'create table foo (val integer);'
        conn = self.ds.dbconnect()
        self.assertEmitted((self.ds, 'executed', _check_cb),
                           conn.execute, sql1)
