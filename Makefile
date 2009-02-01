PYTHON=`which python`
PKGNAME=crunchyfrog
DESTDIR=/
BUILDIR=mydeb
PROJECT=crunchyfrog
VERSION=0.3.2
DEBFLAGS=
PO=`find po/* -maxdepth 0 -name .svn -prune -o -type d|sed 's/po\///g'`

all:
	@echo "make install - Install on local system"
	@echo "make builddeb - Generate a deb package"
	@echo "make clean - Get rid of scratch and byte files"

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

builddeb: dist-clean
	make msg-compile
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

msg-compile:
	@for lang in $(PO); \
	 do msgfmt po/$$lang/LC_MESSAGES/crunchyfrog.po \
	    -o po/$$lang/LC_MESSAGES/crunchyfrog.mo; \
	 done

msg-extract:
	@for i in `find data/glade/ -type f -name "*.glade"`; do \
	 intltool-extract --type=gettext/glade $$i; \
	 done
	xgettext --from-code=UTF-8 -k_ -kN_ \
	  -o po/crunchyfrog.pot `find cf/ -type f -name "*.py"` \
	  `find data/plugins/ -type f -name "*.py"` \
	  data/glade/*.h
	find data/glade/ -type f -name *.h | xargs --no-run-if-empty rm

msg-merge:
	@for lang in $(PO); do \
	  msgmerge -U po/$$lang/LC_MESSAGES/crunchyfrog.po \
	  po/crunchyfrog.pot; done

test:
	$(PYTHON) tests/run.py $@
