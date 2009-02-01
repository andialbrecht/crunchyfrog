PYTHON=`which python`
PKGNAME=crunchyfrog
DESTDIR=/
BUILDIR=mydeb
PROJECT=crunchyfrog
VERSION=0.3.2
DEBFLAGS=

all:
	@echo "make install - Install on local system"
	@echo "make builddeb - Generate a deb package"
	@echo "make clean - Get rid of scratch and byte files"

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

builddeb: dist-clean
	$(PYTHON) setup.py sdist
	mkdir -p $(BUILDIR)/$(PROJECT)-$(VERSION)/debian
	cp dist/$(PROJECT)-$(VERSION).tar.gz $(BUILDIR)
	cd $(BUILDIR) && tar xfz $(PROJECT)-$(VERSION).tar.gz
	mv $(BUILDIR)/$(PROJECT)-$(VERSION).tar.gz $(BUILDIR)/$(PROJECT)-$(VERSION)/
	cp debian/* $(BUILDIR)/$(PROJECT)-$(VERSION)/debian/
	cd $(BUILDIR)/$(PROJECT)-$(VERSION) && dpkg-buildpackage $(DEBFLAGS)

builddeb-src:
	make builddeb DEBFLAGS="-S -k090D660E"

push-ppa: builddeb-src
	cd $(BUILDIR) && dput cf-ppa $(PROJECT)_$(VERSION)*_source.changes

clean:
	$(PYTHON) setup.py clean
	rm -rf build/ MANIFEST $(BUILDIR)
	rm -rf crunchyfrog.egg-info
	find . -name '*.pyc' -delete
	find . -name '*~' -delete
	rm -rf testuserdir

dist-clean: clean
	rm -rf dist
	rm -rf mydeb

msgs-extract:
	$(PYTHON) setup.py extract_messages

msgs-merge:
	$(PYTHON) setup.py update_catalog

test:
	$(PYTHON) tests/run.py $@
