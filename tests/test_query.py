from tests.utils import AppTest

import sqlparse
import sqlparse.sql
from cf.db import Datasource, Query
from cf.db.url import URL


class TestQuery(AppTest):

    def setUp(self):
        super(TestQuery, self).setUp()
        self.ds = Datasource(self.app.datasources)
        self.ds.url = URL('sqlite', database=':memory:')
        self.conn = self.ds.dbconnect()

    def test_parsed(self):
        q = Query('select * from foo', self.conn)
        self.assert_(isinstance(q.parsed, sqlparse.sql.Statement),
                     'Expected sqlparse.sql.Statement, got %r' % q.parsed)
