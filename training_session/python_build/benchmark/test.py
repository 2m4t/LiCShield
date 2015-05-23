#!/usr/bin/env python

"""Wrapper script for running all of Unladen Swallow's third-party tests.

This is equivalent to manually invoking the tests for each third-party app/lib.
Note that this script is intended to be invoked after setup.py install; certain
tests depend on it.

Usage:
    $ /path/to/python test.py  # Run all third-party tests
    $ /path/to/python test.py twisted django  # Only test Twisted and Django
"""

from __future__ import with_statement

__author__ = "collinwinter@google.com (Collin Winter)"

# Python imports
import contextlib
import os
import os.path
import subprocess
import sys
import threading
import time

# We skip psyco because it doesn't build against Unladen Swallow trunk.
# It's still useful for testing against vanilla builds, though.
# Mercurial is disabled due to general flakiness.
# The AppEngine SDK and Rietveld don't ship any tests.
# TODO(collinwinter): add test integration for Spitfire.
SKIP_LIBS = set(["psyco", ".svn", "spitfire", "mercurial", "google_appengine",
                 "rietveld", "spambayes", "lockfile", "html5lib", "bazaar"])


@contextlib.contextmanager
def ChangeDir(new_cwd):
    former_cwd = os.getcwd()
    os.chdir(new_cwd)
    yield
    os.chdir(former_cwd)


class BuildBotMollifier(threading.Thread):

    """Separate thread that periodically prints "Working..." to stdout.

    This is done to prevent scripts (like BuildBot) from assuming that we've
    hung and killing us because long-running tests (I'm looking at you,
    Mercurial) exceed BuildBot's threshold.
    """

    def __init__(self, *args, **kwargs):
        super(BuildBotMollifier, self).__init__(*args, **kwargs)
        self._still_working = False

    def start(self):
        self._still_working = True
        super(BuildBotMollifier, self).start()

    def run(self):
        while True:
            print "Working..."
            # Recover from KeyboardInterrupt and test completion faster than
            # if we just did time.sleep(30).
            for _ in range(6):
                if not self._still_working:
                    return
                time.sleep(5)

    def stop(self):
        self._still_working = False
        self.join()

    def __enter__(self, *args, **kwargs):
        self.start()

    def __exit__(self, *args, **kwargs):
        self.stop()


def BuildEnv(env):
    """Massage an environment variables dict for the host platform.

    Platforms like Win32 require certain env vars to be set.

    Args:
        env: environment variables dict.

    Returns:
        A copy of `env`, possibly with modifications.
    """
    if env == None:
        return env
    fixed_env = env.copy()
    if sys.platform == "win32":
        # Win32 requires certain environment variables be present
        for k in ("COMSPEC", "SystemRoot"):
            if k in os.environ and k not in fixed_env:
                fixed_env[k] = os.environ[k]
    return fixed_env


def CallAndCaptureOutput(command, env=None):
    """Run the given command, capturing stdout and stderr.

    Args:
        command: the command to run as a list, one argument per element.
        env: optional; dict of environment variables to set.

    Returns:
        (output, retcode) where output is captured stdout + stderr as a string;
        retcode is the process's return code.

    Raises:
        RuntimeError: if the command failed. The value of the exception will
        be the error message from the command.
    """
    subproc = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               env=BuildEnv(env))
    with BuildBotMollifier():
        result, err = subproc.communicate()
    print result + err,
    return (result + err, subproc.returncode)


def DefaultPassCheck(command, env=None):
    """Run a test command and check whether it passed.

    This works for most test suites we run, but not all. Pass/fail is
    determined by whether the final line of output starts with OK.

    Args:
        command: the command to run as a list, one argument per element.
        env: optional; dict of environment variables to set.

    Returns:
        True if the test passed, False otherwise.
    """
    output, _ = CallAndCaptureOutput(command, env)
    lines = output.splitlines()
    if not lines:
        return False
    return lines[-1].startswith("OK")


def CheckReturnCode(command, env=None):
    output, ret_code = CallAndCaptureOutput(command, env)
    return ret_code == 0


def GetSubversionVersion():
    subproc = subprocess.Popen(["svn", "--version", "--quiet"],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    result, err = subproc.communicate()
    return map(int, result.split(".")[:2])


### Wrappers for the third-party modules we don't want to break go here. ###

# Tests should return this if they can't run correctly.
SKIP_TEST = object()

def Test2to3():
    return DefaultPassCheck([sys.executable, "-E", "test.py"])

def TestCheetah():
    path = os.pathsep.join([os.environ["PATH"],
                            os.path.dirname(sys.executable)])
    with ChangeDir(os.path.join("src", "Tests")):
        return DefaultPassCheck([sys.executable, "-E", "Test.py"],
                                env={"PATH": path})

def TestCvs2svn():
    return CheckReturnCode([sys.executable, "-E", "run-tests.py", "-v"])

def TestDjango():
    py_path = os.path.join("..", "..", "correctness")
    test_runner = os.path.join("tests", "runtests.py")
    return DefaultPassCheck([sys.executable, test_runner, "-v1",
                             "--settings=django_data.settings"],
                            env={"PYTHONPATH": py_path})

# Mercurial's test are disabled. They fail on Ubuntu Hardy, are flaky on
# Dapper and OS X and take forever to run.
# def TestMercurial():
#     with ChangeDir("tests"):
#         output = CallAndCaptureOutput([sys.executable, "-E", "run-tests.py"])
#         lines = output.splitlines()
#         return lines[-1].endswith(" 0 failed.")

def TestNose():
    return DefaultPassCheck([sys.executable, "-E", "selftest.py"])

def TestNumpy():
    # Numpy refuses to be imported from the source directory.
    with ChangeDir(".."):
        return DefaultPassCheck([sys.executable, "-E", "-c",
                                 "import numpy; numpy.test()"])

def TestPycrypto():
    output, _ = CallAndCaptureOutput([sys.executable, "-E", "test.py"])
    return "***ERROR" not in output

def TestPyopenssl():
    # Note that this is only half the pyOpenSSL test suite, but it's the half
    # we're most interested in.
    return DefaultPassCheck([sys.executable, "-E", "test/test_crypto.py"])

def TestPyxml():
    with ChangeDir("test"):
        output, _ = CallAndCaptureOutput([sys.executable, "-E", "regrtest.py"])
        lines = output.splitlines()
        for line in reversed(lines):
            if line == "All 21 tests OK.":
                return True
        return False

def TestSetuptools():
    return DefaultPassCheck([sys.executable, "-E", "setup.py", "test"])

def TestSqlalchemy():
    return DefaultPassCheck([sys.executable, "-E", "test/alltests.py"])

def TestSwig():
    return CheckReturnCode(["make", "check"])

def TestSympy():
    output, _ = CallAndCaptureOutput([sys.executable, "-E", "setup.py", "test"])
    return not output.endswith("DO *NOT* COMMIT!\n")

def TestTwisted():
    # Make sys.executable take precedence over other python binaries. I don't
    # see that trial has a way to pass this kind of thing in as an argument.
    path = os.pathsep.join([os.path.dirname(sys.executable),
                            os.environ["PATH"]])
    return CheckReturnCode(["trial", "twisted"], env={"PATH": path})

def TestZodb():
    # This doesn't work with Subversion 1.6+ because of bugs in setuptools.
    if GetSubversionVersion() >= [1, 6]:
        print "Skipping ZODB: doesn't work with Subversion 1.6+"
        return SKIP_TEST
    bin_dir = os.path.dirname(sys.executable)
    test_runner = os.path.join(bin_dir, "zope-testrunner")
    import ZODB
    zodb_dir = os.path.dirname(os.path.dirname(ZODB.__file__))
    return CheckReturnCode([sys.executable, test_runner, "--all", "--test-path",
                            zodb_dir])

def TestZope_interface():
    # zope.interface is included because Twisted and a number of Zope packages
    # depend on it.
    return DefaultPassCheck([sys.executable, "-E", "setup.py", "test",
                             "-s", "zope.interface.tests"])


### Utility code ###

def FindThirdPartyLibs(basedir):
    """Enumerate the subdirectories of the given base directory.

    Note that this will skip any .svn directories.

    Args:
        basedir: name of the directory for which to enumerate subdirectories.

    Yields:
        (dirname, relpath) 2-tuples, where dirname is the name of the
        subdirectory, and relpath is the relative path to the subdirectory from
        the current working directory.
    """
    for filename in os.listdir(basedir):
        entry = os.path.join(basedir, filename)
        if os.path.isdir(entry) and filename not in SKIP_LIBS:
            yield (filename, entry)


if __name__ == "__main__":
    restrict = None
    if len(sys.argv) > 1:
        # Allow the user to limit which third-party tests are run. sys.argv[1:]
        # should be a list of lower-case test names, e.g., "django", "twisted".
        restrict = set(sys.argv[1:])

    basedir = os.path.join(os.path.split(__file__)[0], "lib")
    tests_passed = {}
    for dirname, subdir in FindThirdPartyLibs(basedir):
        test_name = dirname.capitalize()
        test_func = globals().get("Test" + test_name)
        if not test_func:
            print "No tests defined for", test_name
        elif restrict is None or dirname in restrict:
            print "Testing", test_name
            current_dir = os.getcwd()
            os.chdir(subdir)
            try:
                tests_passed[test_name] = test_func()
            finally:
                os.chdir(current_dir)
                print "Done testing", test_name

    skipped = [k for k, v in tests_passed.items() if v is SKIP_TEST]
    if skipped:
        print "SKIPPED:", skipped

    if all(tests_passed.values()):
        print "All OK"
    else:
        failed = [test for (test, passed) in tests_passed.items() if not passed]
        print "FAILED:", failed
        sys.exit(1)
