import unittest

from cf.db.url import URL


class TestURL(unittest.TestCase):

    def test_clean_port(self):
        url = URL('foo', port=None)
        self.assertEqual(url.port, None)
        url = URL('foo', port=123)
        self.assertEqual(url.port, 123)
        url = URL('foo', port='123')
        self.assertEqual(url.port, 123)
        url = URL('foo', port=' 123')
        self.assertEqual(url.port, 123)
        url = URL('foo', port='123 ')
        self.assertEqual(url.port, 123)
        url = URL('foo', port='123a')
        self.assertEqual(url.port, None)
        url = URL('foo', port='abc')
        self.assertEqual(url.port, None)
