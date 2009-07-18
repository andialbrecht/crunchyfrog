# -*- coding: utf-8 -*-

from utils import AppTest


class TestApp(AppTest):

    def test_instances(self):
        i1 = self.app.new_instance()
        i2 = self.app.new_instance()
        self.assertNotEqual(i1, i2)
        self.assertEqual(self.app.get_instances(), [i1, i2])
        self.assertEqual(i1.app, self.app)
        self.assertEqual(i2.app, self.app)
        i1.destroy()
        self.assertEqual(self.app.get_instances(), [i2])
        i2.destroy()
        self.assertEqual(self.app.get_instances(), [])
