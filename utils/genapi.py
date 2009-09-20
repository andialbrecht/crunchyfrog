#!/usr/bin/env python

import os
import pydoc


HEADER = '=-^""""""'
PACKAGES = ["cf"]
BASE_DIR = os.path.abspath(".")
OUT_DIR = os.path.abspath('docs/devguide/source/api/')


def _build_pkg(name, base=BASE_DIR, output=None, level=0, modname=None):
    if modname is None:
        modname = name
    modules = {}
    fullpath = os.path.join(base, name)
    for dirpath, dirnames, filenames in os.walk(fullpath):
        pyfiles = [x for x in filenames if x.endswith('.py')]
        if not pyfiles:
            continue
        modname = dirpath.replace(base, '').replace('/', '.')[1:]
        fname = os.path.join(dirpath, '__init__.py')
        if not os.path.exists(fname):   # Package data
            continue
        s = pydoc.source_synopsis(open(fname)) or "[undocumented]"
        modules[modname] = s.strip()
        for pyfile in pyfiles:
            if pyfile == '__init__.py':
                continue
            xmodname = '.'.join([modname, pyfile.replace('.py', '')])
            fname = os.path.join(dirpath, pyfile)
            s = pydoc.source_synopsis(open(fname)) or "[undocumented]"
            modules[xmodname] = s.strip()
    keys = modules.keys()
    keys.sort()
    for k in keys:
        output = []
        header = ':mod:`%s` -- %s' % (k, modules[k])
        output.append(header)
        output.append(HEADER[k.count('.')]*len(header))
        output.append('')
        output.append('.. automodule:: %s' % k)
        output.append('   :members:')
        output.append('   :synopsis: %s' % modules[k])
        output.append('')
        f = open(os.path.join(OUT_DIR, '%s.rst' % k.replace('.', '_')), 'w')
        f.write('\n'.join(output))
        f.close()

def main():
    for pkg in PACKAGES:
        fname = os.path.join(BASE_DIR, pkg, '__init__.py')
        synopsis = pydoc.source_synopsis(open(fname)) or ''
        header = ':mod:`%s` -- %s' % (pkg, synopsis.strip())
        output = ['*'*len(header), header, '*'*len(header), '']
        output.append('.. toctree::')
        output.append('   :glob:')
        output.append('')
        output.append('   %s_*' % pkg)
        _build_pkg(pkg, output=output, level=0)
        # We've just one package, so we write it out as index.rst.
        # Replace this to '%s.rst' % pkg if we've more than one... ;-)
        f = open(os.path.join(OUT_DIR, 'index.rst'), 'w')
        f.write('\n'.join(output))
        f.close()


if __name__ == "__main__":
    main()

