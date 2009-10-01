import glob
import unittest


class TestGTKRequirements(unittest.TestCase):

    def test_required_version(self):
        # Make sure all Glade files require GTK 2.12
        test_string = '<!-- interface-requires gtk+ 2.12 -->'
        for fname in glob.glob('data/glade/*.glade'):
            xml = open(fname).read()
            self.assert_(test_string in xml,
                         'Invalid GTK requirement: %s' % fname)
