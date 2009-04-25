all: clean
	zip django_backend.zip django_backend/*
	
clean:
	find . -name "*.pyc" -print | xargs rm -rf
	
install: all
	rm -f ~/.crunchyfrog/plugins/django_backend.zip
	mv django_backend.zip ~/.crunchyfrog/plugins/django_backend.zip