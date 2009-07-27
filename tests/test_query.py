from tests.utils import DbTest

import sqlparse
import sqlparse.sql
from cf.db import Query


class TestQuery(DbTest):

    def setUp(self):
        super(TestQuery, self).setUp()
        self.conn = self.ds.dbconnect()

    def test_parsed(self):
        q = Query('select * from foo', self.conn)
        self.assert_(isinstance(q.parsed, sqlparse.sql.Statement),
                     'Expected sqlparse.sql.Statement, got %r' % q.parsed)
