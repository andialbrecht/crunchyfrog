import os

from utils import AppTest

PG_URL = 'postgres://postgres@/avsweb'

import cf.db

class TestDBBase(AppTest):

    URL = 'sqlite:////tmp/cftest.db'

    def setUp(self):
        AppTest.setUp(self)
        manager = cf.db.DatasourceManager(self.app)
        self.datasource = cf.db.Datasource(manager)
        url = cf.db.url.make_url(self.URL)
        self.datasource.url = url
        if url.drivername == 'sqlite':
            if os.path.isfile(url.database):
                os.remove(url.database)
        self.con1 = self.datasource.dbconnect()
        self.con2 = self.datasource.dbconnect()
        self.con1.execute('create table cf_test (val integer)')

    def tearDown(self):
        self.con1.execute('drop table cf_test')
        self.con1.close()
        self.con2.close()

    def test_select(self):
        self.con1.execute('insert into cf_test (val) values (1)')
        test = self.con1.execute('select count(*) from cf_test')[0][0]
        self.assertEqual(test, 1)
        self.con1.execute('delete from cf_test')
        test = self.con1.execute('select count(*) from cf_test')[0][0]
        self.assertEqual(test, 0)

    def test_transaction(self):
        self.con1.begin()
        self.con1.execute('insert into cf_test (val) values (1)')
        test = self.con2.execute('select count(*) from cf_test')[0][0]
        self.assertEqual(test, 0)
        test = self.con1.execute('select count(*) from cf_test')[0][0]
        self.assertEqual(test, 1)
        self.con1.commit()
        test = self.con2.execute('select count(*) from cf_test')[0][0]
        self.assertEqual(test, 1)

    def test_rollback(self):
        self.con1.begin()
        self.con1.execute('insert into cf_test (val) values (1)')
        test = self.con2.execute('select count(*) from cf_test')[0][0]
        self.assertEqual(test, 0)
        test = self.con1.execute('select count(*) from cf_test')[0][0]
        self.assertEqual(test, 1)
        self.con1.rollback()
        test = self.con2.execute('select count(*) from cf_test')[0][0]
        self.assertEqual(test, 0)
        test = self.con1.execute('select count(*) from cf_test')[0][0]
        self.assertEqual(test, 0)

    def test_transaction_state(self):
        state = self.con1.get_property('transaction-state')
        self.assertEqual(state, cf.db.TRANSACTION_IDLE)
        self.con1.begin()
        self.refresh_gui()
        state = self.con1.get_property('transaction-state')
        self.assertEqual(state, cf.db.TRANSACTION_ACTIVE)
        state = self.con2.get_property('transaction-state')
        self.assertEqual(state, cf.db.TRANSACTION_IDLE)
        self.con2.begin()
        self.refresh_gui()
        state = self.con1.get_property('transaction-state')
        self.assertEqual(state, cf.db.TRANSACTION_ACTIVE)
        state = self.con2.get_property('transaction-state')
        self.assertEqual(state, cf.db.TRANSACTION_ACTIVE)
        self.con2.execute('rollback')
        self.con2.update_transaction_state()
        self.refresh_gui()
        state = self.con2.get_property('transaction-state')
        self.assertEqual(state, cf.db.TRANSACTION_IDLE)
        state = self.con1.get_property('transaction-state')
        self.assertEqual(state, cf.db.TRANSACTION_ACTIVE)
        self.con1.rollback()
        self.refresh_gui()
        state = self.con2.get_property('transaction-state')
        self.assertEqual(state, cf.db.TRANSACTION_IDLE)


class TestPG(TestDBBase):
    URL = PG_URL
