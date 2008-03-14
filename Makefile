PO=de
RELEASENAME=snapshot
PYTHON=`which python`

clean: po-clean
	find . -name "*.pyc" -delete
	find . -name "*~" -delete
	rm -rf build/
	
ChangeLog:
	svn2cl --authors=AUTHORS -o ChangeLog --group-by-day
	
dist-prepare: clean ChangeLog
	
egg: dist-prepare
	python setup.py bdist_egg
	
deb: dist-prepare
	rm -rf /tmp/crunchyfrog-build
	mkdir -p /tmp/crunchyfrog-build/crunchyfrog
	cp -r * /tmp/crunchyfrog-build/crunchyfrog/
	cd /tmp/crunchyfrog-build/crunchyfrog/; dpkg-buildpackage -us -uc -rfakeroot
	mkdir -p dist
	cp /tmp/crunchyfrog-build/*.deb dist/
	rm -rf /tmp/crunchyfrog-build
	
snapshot: dist-prepare
	python setup.py egg_info -rbdev bdist_egg rotate -m.egg -k3

dist-release: dist-prepare sdist-release bdist-release

sdist-release:
	$(PYTHON) setup.py egg_info -b-$(RELEASENAME) sdist

sdist-upload:
	$(PYTHON) setup.py egg_info -b-$(RELEASENAME) sdist upload

bdist-release:
	$(PYTHON) setup.py egg_info -b-$(RELEASENAME) bdist_egg
	
source-release: dist-prepare
	$(PYTHON) setup.py egg_info -rbdev sdist upload
	
sdist: dist-prepare
	$(PYTHON) setup.py sdist
	
po-clean:
	find data -type f -name *.h -print | xargs --no-run-if-empty rm -rf
	find cf -type f -name *.h -print | xargs --no-run-if-empty rm -rf

po-data:
	for lang in $(PO); do msgfmt po/$$lang/LC_MESSAGES/crunchyfrog.po -o po/$$lang/LC_MESSAGES/crunchyfrog.mo;done
	
po-gen:
	intltool-extract --type=gettext/glade data/crunchyfrog.glade
	xgettext --from-code=UTF-8 -k_ -kN_ -o po/crunchyfrog.pot `find cf/ -type f -name *.py` data/*.h `find cf -type f -name *.h`
	for lang in $(PO); do msgmerge -U po/$$lang/LC_MESSAGES/crunchyfrog.po po/crunchyfrog.pot; done
	
api:
	PYTHONPATH=`pwd`/data/:`pwd` apydia -c data/apydia.ini
	cp docs/api/cf.html docs/api/index.html
