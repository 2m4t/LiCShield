#!/usr/bin/env python

"""Wrapper script for building all of Unladen Swallow's third-party tests.

This is equivalent to manually invoking setup.py in each lib/ directory, except
in cases like swig, where configure/make is invoked.
"""

__author__ = "collinwinter@google.com (Collin Winter)"

# Python imports
import os
import os.path
import shutil
import subprocess
import sys

# We skip psyco because it doesn't build against Unladen Swallow.
# The AppEngine SDK doesn't have any tests, but is used by some benchmarks.
# Rietveld and html5lib don't ship with any tests.
SKIP_LIBS = set(["psyco", ".svn", "google_appengine", "rietveld", "html5lib",
                 "bazaar"])


class swig(object):

    def build(self):
        # This prefix is used because the continuous build is configured to
        # delete python_prefix, so this will take care of cleaning up swig as
        # well. Note that swig isn't actually installed, so this is just to be
        # sure that we're not polluting /usr/... with potentially-busted swig
        # installations.
        python_prefix = os.path.dirname(os.path.dirname(sys.executable))
        swig_prefix = os.path.join(python_prefix, "swig")

        subprocess.check_call(["./configure", "--without-perl5",
                               "--without-java", "--without-ruby",
                               "--without-php", "--disable-ccache",
                               "--prefix=" + swig_prefix,
                               "--without-tcl", "--without-r",
                               "--with-python=" + sys.executable])
        subprocess.check_call(["make"])

    def install(self):
        # This intentionally doesn't install anything. We only install Python
        # modules/scripts because some tests require them. In this case,
        # we don't need to install swig for it to work. This is here to make
        # test.py's life easier, not to serve as a general-purpose setup.py
        # wrapper.
        self.build()

    def clean(self):
        subprocess.call(["make", "clean"])


class zodb(object):

    def build(self):
        subprocess.check_call([sys.executable, "-E", "bootstrap.py"])
        subprocess.check_call([sys.executable, "-E", "bin/buildout"])

    def install(self):
        self.build()
        subprocess.call([sys.executable, "-E", "setup.py", "install"])

    def clean(self):
        subprocess.call([sys.executable, "-E", "setup.py", "clean"])


def SetupSubdir(subdir, argv):
    """Run the setup.py command in the given subdir.

    Args:
        subdir: a directory relative to the current working directory where
            the setup.py command should be run.
        argv: list of arguments given to setup.py. Example: ["clean"].
    """
    current_dir = os.getcwd()
    os.chdir(subdir)
    try:
        setup_class = globals().get(os.path.basename(subdir))
        if setup_class:
            # This translates to, e.g., swig().build().
            getattr(setup_class(), argv[0])()
        else:
            subprocess.check_call([sys.executable, "setup.py"] + argv)
    finally:
        os.chdir(current_dir)


def CleanSubdir(subdir):
    """Simulate setup.py clean --all for a given subdirectory.

    We simulate this, instead of actually running the command, so that we
    don't have to deal with dependencies on setuptools just to rm -fr build.
    """
    shutil.rmtree(os.path.join(subdir, "build"), ignore_errors=True)


def SortLibs(libs):
    """Sort the third-party libraries as they should be installed.

    Args:
        libs: iterable of library paths.

    Returns:
        The input iterable `libs` as a list, sorted in the order they should
        be processed.
    """
    def KeyFunc(lib):
        priority = 100  # Higher numbers are sorted later in the list.
        if lib.endswith("setuptools") or lib.endswith("zope_interface"):
            priority = 0
        return (priority, lib)

    return sorted(libs, key=KeyFunc)


def FindThirdPartyLibs(basedir):
    """Enumerate the subdirectories of the given base directory.

    Note that this will skip any .svn directories.

    Args:
        basedir: name of the directory for which to enumerate subdirectories.

    Yields:
        Directory names relative the current working directory.
    """
    for filename in os.listdir(basedir):
        entry = os.path.join(basedir, filename)
        if os.path.isdir(entry) and filename not in SKIP_LIBS:
            yield entry


if __name__ == "__main__":
    action = sys.argv[1]
    if action not in ("build", "clean", "install"):
        raise ValueError("Invalid action: %r" % action)

    basedir = os.path.join(os.path.split(__file__)[0], "lib")
    for subdir in SortLibs(FindThirdPartyLibs(basedir)):
        if action == "clean":
            print "### Cleaning", subdir
            CleanSubdir(subdir)
        else:
            print "### Setting up", subdir
            SetupSubdir(subdir, sys.argv[1:])
