#!/usr/bin/env python

"""Tests for utility functions in perf.py."""

__author__ = "collinwinter@google.com (Collin Winter)"

# Python imports
import unittest

# Local imports
import perf


class Object(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# There's no particular significance to these values.
DATA1 = [89.2, 78.2, 89.3, 88.3, 87.3, 90.1, 95.2, 94.3, 78.3, 89.3]
DATA2 = [79.3, 78.3, 85.3, 79.3, 88.9, 91.2, 87.2, 89.2, 93.3, 79.9]


class TestStatsFunctions(unittest.TestCase):

    def testSampleStdDev(self):
        result = perf.SampleStdDev([1, 2, 3, 4, 5])
        self.assertAlmostEqual(result, 1.58, places=2)

    def testPooledSampleVariance(self):
        result = perf.PooledSampleVariance(DATA1, DATA2)
        self.assertAlmostEqual(result, 31.782, places=3)

        # Should be the same result, regardless of the input order.
        result = perf.PooledSampleVariance(DATA2, DATA1)
        self.assertAlmostEqual(result, 31.782, places=3)

    def testTScore(self):
        self.assertAlmostEqual(perf.TScore(DATA1, DATA2), 1.0947, places=4)
        self.assertAlmostEqual(perf.TScore(DATA2, DATA1), -1.0947, places=4)

    def testIsSignificant(self):
        (significant, _) = perf.IsSignificant(DATA1, DATA2)
        self.assertFalse(significant)
        (significant, _) = perf.IsSignificant(DATA2, DATA1)
        self.assertFalse(significant)

        inflated = [x * 10 for x in DATA1]
        (significant, _) = perf.IsSignificant(inflated, DATA1)
        self.assertTrue(significant)
        (significant, _) = perf.IsSignificant(DATA1, inflated)
        self.assertTrue(significant)


# Sample smaps sections from ssh-agent running on Ubuntu.
SMAPS_DATA = """
08047000-08059000 r-xp 00000000 08:01 41130                              /usr/bin/ssh-agent
Size:                72 kB
Rss:                 56 kB
Shared_Clean:         0 kB
Shared_Dirty:         0 kB
Private_Clean:       56 kB
Private_Dirty:        0 kB
08059000-0805a000 rw-p 00011000 08:01 41130                              /usr/bin/ssh-agent
Size:                 4 kB
Rss:                  4 kB
Shared_Clean:         0 kB
Shared_Dirty:         0 kB
Private_Clean:        0 kB
Private_Dirty:        4 kB
0805a000-0807d000 rw-p 0805a000 00:00 0                                  [heap]
Size:               140 kB
Rss:                 56 kB
Shared_Clean:         0 kB
Shared_Dirty:         0 kB
Private_Clean:        0 kB
Private_Dirty:       56 kB
45f48000-45f5d000 r-xp 00000000 08:01 1079490                            /lib/ld-2.3.6.so
Size:                84 kB
Rss:                  0 kB
Shared_Clean:         0 kB
Shared_Dirty:         0 kB
Private_Clean:        0 kB
Private_Dirty:        0 kB
"""

class TestSmaps(unittest.TestCase):

    def testParseSmapsData(self):
        self.assertEqual(perf._ParseSmapsData(SMAPS_DATA), 116)


class TestMisc(unittest.TestCase):

    def test_SummarizeData(self):
        result = perf.SummarizeData([], points=3)
        self.assertEqual(result, [])

        result = perf.SummarizeData(range(3), points=3)
        self.assertEqual(result, range(3))

        result = perf.SummarizeData(range(10), points=5)
        self.assertEqual(result, [1, 3, 5, 7, 9])

        result = perf.SummarizeData(range(9), points=5)
        self.assertEqual(result, [1, 3, 5, 7, 8])

        result = perf.SummarizeData(range(10), points=5, summary_func=min)
        self.assertEqual(result, [0, 2, 4, 6, 8])


    def testParseBenchmarksOption(self):
        # perf.py, no -b option.
        should_run = perf.ParseBenchmarksOption("")
        self.assertEqual(should_run, set(["2to3", "django", "slowpickle",
                                          "slowspitfire", "slowunpickle"]))

        # perf.py -b 2to3
        should_run = perf.ParseBenchmarksOption("2to3")
        self.assertEqual(should_run, set(["2to3"]))

        # perf.py -b 2to3,pybench
        should_run = perf.ParseBenchmarksOption("2to3,pybench")
        self.assertEqual(should_run, set(["2to3", "pybench"]))

        # perf.py -b -2to3
        should_run = perf.ParseBenchmarksOption("-2to3")
        self.assertEqual(should_run, set(["django", "slowspitfire",
                                          "slowpickle", "slowunpickle"]))

        # perf.py -b all
        should_run = perf.ParseBenchmarksOption("all")
        self.assertTrue("django" in should_run, should_run)
        self.assertTrue("pybench" in should_run, should_run)

        # perf.py -b -2to3,all
        should_run = perf.ParseBenchmarksOption("-2to3,all")
        self.assertTrue("django" in should_run, should_run)
        self.assertTrue("pybench" in should_run, should_run)
        self.assertFalse("2to3" in should_run, should_run)

        # Error conditions
        self.assertRaises(ValueError, perf.ParseBenchmarksOption, "-all")

if __name__ == "__main__":
    unittest.main()
