all: clean
	zip httplog_backend.zip httplog_backend/*
	
clean:
	find . -name "*.pyc" -print | xargs rm -rf
	
install: all
	rm -f ~/.crunchyfrog/plugins/httplog_backend.zip
	mv httplog_backend.zip ~/.crunchyfrog/plugins/httplog_backend.zip