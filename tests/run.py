#!/usr/bin/env python

"""Run test cases.

The command line script accepts regular expressions as command line arguments.
Those patterns are used to determine which test cases should be executed.
If not command line arguments are given all test cases are considered.

For example

  python tests/run.py datasources config

runs 'test_datasources.py' and 'test_config.py'.
"""

import os
import re
import sys
import unittest

TESTDIR = os.path.abspath(os.path.dirname(__file__))

sys.path.insert(0, os.path.join(TESTDIR, '../'))
sys.path.insert(0, TESTDIR)


def main():
    cmdline_patterns = []
    for pattern in sys.argv[1:]:
        cmdline_patterns.append(re.compile(pattern, re.IGNORECASE))
    test_modules = []
    for fname in os.listdir(TESTDIR):
        if not os.path.splitext(fname)[-1] == '.py' \
        or not fname.startswith('test_'):
            continue
        if cmdline_patterns:
            for pattern in cmdline_patterns:
                if pattern.search(fname):
                    test_modules.append(os.path.splitext(fname)[0])
                    break
        else:
            test_modules.append(os.path.splitext(fname)[0])
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for mod_name in test_modules:
        mod = __import__(mod_name)
        suite.addTests(loader.loadTestsFromModule(mod))
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    main()
