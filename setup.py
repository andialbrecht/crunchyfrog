from setuptools import setup, find_packages
import os

from cf import release

data_files = [
    ("share/pixmaps", [os.path.abspath("data/crunchyfrog.png")]),
    ("man/man1", ["data/crunchyfrog.1"]),
    ("share/applications", ["data/crunchyfrog.desktop"]),
    ("share/crunchyfrog", [os.path.abspath("data/crunchyfrog.glade")]),
    ("share/icons/hicolor/scalable/apps", [os.path.abspath("data/crunchyfrog.svg")])
]
for item in os.listdir("po/"):
    if not os.path.isdir(os.path.join("po/", item)) \
    or item == ".svn" \
    or not os.path.isfile(os.path.join("po/", item, "LC_MESSAGES/crunchyfrog.mo")):
        continue
    data_files.append(("share/locale/%s/LC_MESSAGES" % item, ["po/%s/LC_MESSAGES/crunchyfrog.mo" % item]))

setup(
    data_files=data_files,
    name=release.appname,
    version=release.version,
    description=release.description,
    author=release.author,
    author_email=release.author_email,
    long_description=release.long_description,
    license="GPL",
    url=release.url,
    classifiers = [
        "Development Status :: 3 - Alpha",
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
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
    install_requires = [
        "ConfigObj >= 4.4.0",
        "lxml >= 0.9",
        "kiwi >= 1.9.16", 
    ],
    entry_points="""
    [gui_scripts]
    crunchyfrog = cf:main
    
    [crunchyfrog.backend]
    postgres = cf.backends.postgres:PostgresBackend
    sqlite = cf.backends.sqlite:SQLiteBackend
    mysql = cf.backends.mysql:MySQLBackend
    oracle = cf.backends.oracle:OracleBackend
    ldap = cf.backends.ldapbe:LDAPBackend
    
    [crunchyfrog.plugin]
    cfshell = cf.shell:CFShell
    refbrowser = cf.ui.refviewer:ReferenceViewer
    library = cf.library:SQLLibraryPlugin
    
    [crunchyfrog.export]
    csv = cf.filter.exportfilter:CSVExportFilter
    odc = cf.filter.exportfilter:OOCalcExportFilter
    """
)
