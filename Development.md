### Getting the Sources ###

To check out the latest sources from Subversion use the "Sources" tab
above and follow the instructions on that page.

A preliminary API reference is available
[here](http://crunchyfrog.googlecode.com/svn/docs/devguide/index.html).


### Contributing ###

Please file bug reports and feature requests on the project
site at http://code.google.com/p/crunchyfrog/issues/entry or if you
have code to contribute upload it to http://codereview.appspot.com and add
albrecht.andi@googlemail.com as reviewer. For more information about the
review tool and how to use it visit it's project page:
http://code.google.com/p/rietveld


### Profiling ###

To profile this application set the CF\_PROFILE environment variable, e.g.
by running

```
CF_PROFILE=1 ./crunchyfrog
```

from the directory where you've checked out the sources. The profile data
is saved to a file called ```crunchyfrog.prof``` in the current working
directory. You can convert the collected data with ```hotshot2calltree``` to
view it with **kcachegrind**:

```
$ hotshot2calltree -o crunchyfrog.kgrind crunchyfrog.prof
$ kcachegrind crunchyfrog.kgrind
```