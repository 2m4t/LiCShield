#!/usr/bin/env python2.5

"""Main test file for 2to3.

Running "python test.py" will run all tests in tests/test_*.py.
"""
# Author: Collin Winter

import unittest
from lib2to3 import tests
import lib2to3.tests.support
from sys import exit, argv

if "-h" in argv or "--help" in argv or len(argv) > 2:
    print "Usage: %s [-h] [test suite[.test class]]" %(argv[0])
    print "default   : run all tests in lib2to3/tests/test_*.py"
    print "test suite: run tests in lib2to3/tests/<test suite>"
    print "test class : run tests in <test suite>.<test class>"
    exit(1)

if len(argv) == 2:
    mod = tests
    for m in argv[1].split("."):
        mod = getattr(mod, m, None)
        if not mod:
            print "Error importing %s" %(m)
            exit(1)

    if argv[1].find(".") == -1:
        # Just the module was specified, load all the tests
        suite = unittest.TestLoader().loadTestsFromModule(mod)
    else:
        # A class was specified, load that
        suite = unittest.makeSuite(mod)
else:
    suite = tests.all_tests

try:
    tests.support.run_all_tests(tests=suite)
except KeyboardInterrupt:
    pass
