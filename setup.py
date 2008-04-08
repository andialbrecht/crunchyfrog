from setuptools import setup
import os
import sys

if "install" in sys.argv or os.getuid() == 0:
    print "To install CrunchyFrog run"
    print 
    print "\tmake"
    print "\tmake install"
    print
    print "See README for additional information."
    sys.exit(1)

from cf import release

setup(
    name=release.appname,
    version=release.version,
    description=release.description,
    author=release.author,
    author_email=release.author_email,
    long_description=release.long_description,
    license="GPL",
    url=release.url,
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: Gnome",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Topic :: Database :: Front-Ends",
        "Topic :: Desktop Environment :: Gnome",
    ],
    include_package_data=True,
)
