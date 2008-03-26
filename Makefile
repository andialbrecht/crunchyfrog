#/usr/bin/make -f

PREFIX ?= /usr
BINDIR=$(PREFIX)/bin
LIBDIR=$(PREFIX)/lib/crunchyfrog
DATADIR=$(PREFIX)/share
APPDATADIR=$(DATADIR)/crunchyfrog
LOCALEDIR=$(PREFIX)/locale
MANDIR=$(PREFIX)/man

PO=de
RELEASENAME=snapshot
PYTHON=python

CF_PKGS=$(shell find cf -type d ! -path "*/.svn*")
CF_MODULES=$(shell find cf -type f ! -path "*/.svn*" ! -name "*.pyc")
CF_PLUGIN_PKGS=$(shell find data/plugins/* -type d ! -path "*/.svn*")
CF_PLUGIN_MODULES=$(shell find data/plugins/* -type f ! -path "*/.svn*" ! -name "*.pyc")

#GTKMOZEMBED_PATH = $(shell pkg-config --libs-only-L mozilla-gtkmozembed 2>/dev/null || pkg-config --libs-only-L firefox-gtkmozembed 2>/dev/null | sed -e "s/-L//g" -e "s/[  ]//g" )
GTKMOZEMBED_PATH=/usr/lib/firefox

CONFIGURE_IN = sed -e 's!GTKMOZEMBED_PATH!MOZILLA_FIVE_HOME=$(GTKMOZEMBED_PATH) LD_LIBRARY_PATH=$(GTKMOZEMBED_PATH)!g' -e 's!LIBDIR!$(LIBDIR)!g' -e 's!DATADIR!$(DATADIR)!g' -e 's!PREFIX!$(PREFIX)!g' -e 's!BINDIR!$(BINDIR)!g' -e 's!LOCALEDIR!$(LOCALEDIR)!g'

FILES_IN = data/crunchyfrog.in cf/dist.py.in

all: clean
	for fn in $(FILES_IN) ; do \
		IN=`cat $$fn | $(CONFIGURE_IN)`; \
		F_OUT=`echo $$fn | sed -e 's/\.in$$//g'`; \
		echo "$$IN" > $$F_OUT; \
	done
	@echo "Type: make install now"

clean: po-clean
	find . -name "*.pyc" -print | xargs rm -rf
	find . -name "*~" -print | xargs rm -rf
	rm -rf build/
	
ChangeLog:
	svn2cl --authors=AUTHORS -o ChangeLog --group-by-day
	
dist-prepare: clean ChangeLog

dist-clean: dist-prepare
	find . -path "*.svn*" -print | xargs rm -rf
	rm -rf dist/
	
deb: dist-prepare
	rm -rf /tmp/crunchyfrog-build
	mkdir -p /tmp/crunchyfrog-build/crunchyfrog
	cp -r * /tmp/crunchyfrog-build/crunchyfrog/
	${MAKE} -C /tmp/crunchyfrog-build/crunchyfrog/ dist-clean
	cd /tmp/crunchyfrog-build/crunchyfrog/; dpkg-buildpackage -us -uc -rfakeroot
	mkdir -p dist
	cp /tmp/crunchyfrog-build/*.deb dist/
	rm -rf /tmp/crunchyfrog-build

dist-release: dist-prepare sdist-release

sdist-release:
	$(PYTHON) setup.py egg_info -b-$(RELEASENAME) sdist

sdist-upload:
	$(PYTHON) setup.py egg_info -b-$(RELEASENAME) sdist upload
	
sdist: dist-prepare
	$(PYTHON) setup.py egg_info -b-$(RELEASENAME) sdist
	
po-clean:
	find data -type f -name *.h -print | xargs --no-run-if-empty rm -rf
	find cf -type f -name *.h -print | xargs --no-run-if-empty rm -rf
	
make-install-dirs:
	mkdir -p $(DESTDIR)$(BINDIR)
	mkdir -p $(DESTDIR)$(LIBDIR)/cf
	for pkg in $(CF_PKGS); do mkdir -p $(DESTDIR)$(LIBDIR)/$$pkg; done
	mkdir -p $(DESTDIR)$(APPDATADIR)
	for pkg in $(CF_PLUGIN_PKGS); do \
		DEST=`echo "$$pkg"|sed -e 's!data/plugins/!!g'`; \
		mkdir -p $(DESTDIR)$(APPDATADIR)/plugins/$$DEST; \
	done
	for lang in $(PO); do mkdir -p $(DESTDIR)$(LOCALEDIR)/$$lang/LC_MESSAGES; done
	mkdir -p $(DESTDIR)$(DATADIR)/applications
	mkdir -p $(DESTDIR)$(MANDIR)/man1
	mkdir -p $(DESTDIR)$(DATADIR)/pixmaps
	mkdir -p $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps
	
install: make-install-dirs
	for mod in $(CF_MODULES); do install -m 644 $$mod $(DESTDIR)$(LIBDIR)/$$mod; done
	install -m 644 data/crunchyfrog.glade $(DESTDIR)$(APPDATADIR)/
	for mod in $(CF_PLUGIN_MODULES); do \
		DEST=`echo "$$mod"|sed -e 's!data/plugins/!!g'`; \
		install -m 644 $$mod $(DESTDIR)$(APPDATADIR)/plugins/$$DEST; \
	done
	for lang in $(PO); do install -m 644 po/$$lang/LC_MESSAGES/crunchyfrog.mo $(DESTDIR)$(LOCALEDIR)/$$lang/LC_MESSAGES/crunchyfrog.mo; done
	install -m 644 data/crunchyfrog.desktop $(DESTDIR)$(DATADIR)/applications/
	install -m 755 data/crunchyfrog $(DESTDIR)$(BINDIR) 
	install -m 644 data/crunchyfrog.1 $(DESTDIR)$(MANDIR)/man1/
	install -m 644 data/crunchyfrog.png $(DESTDIR)$(DATADIR)/pixmaps/
	install -m 644 data/crunchyfrog.svg $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/

po-data:
	for lang in $(PO); do msgfmt po/$$lang/LC_MESSAGES/crunchyfrog.po -o po/$$lang/LC_MESSAGES/crunchyfrog.mo;done
	
po-gen:
	intltool-extract --type=gettext/glade data/crunchyfrog.glade
	xgettext --from-code=UTF-8 -k_ -kN_ -o po/crunchyfrog.pot `find cf/ -type f -name *.py` data/*.h `find cf -type f -name *.h`
	for lang in $(PO); do msgmerge -U po/$$lang/LC_MESSAGES/crunchyfrog.po po/crunchyfrog.pot; done
	
api:
	PYTHONPATH=`pwd`/data/:`pwd` apydia -c data/apydia.ini
	cp docs/api/cf.html docs/api/index.html
