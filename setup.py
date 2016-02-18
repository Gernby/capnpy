import sys
import os
from setuptools import setup, find_packages, Extension

USE_CYTHON = os.environ.get('USE_CYTHON', 'auto')
if USE_CYTHON == 'auto':
    is_pypy = hasattr(sys, 'pypy_version_info')
    USE_CYTHON = not is_pypy
else:
    USE_CYTHON = int(USE_CYTHON)


if USE_CYTHON:
    from Cython.Build import cythonize

    files = ["capnpy/blob.py",
             "capnpy/struct_.py",
             "capnpy/type.py",
             "capnpy/ptr.pyx",
             "capnpy/unpack.pyx",
             "capnpy/_util.pyx"]

    def getext(fname):
        extname = fname.replace('/', '.').replace('.pyx', '').replace('.py', '')
        return Extension(extname, [fname])

    ext_modules = cythonize(map(getext, files), gdb_debug=False)

else:
    ext_modules = []

setup(name="capnpy",
      version="0.1",
      packages = find_packages(),
      package_data = {
          'capnpy': ['*.capnp', '*.pyx']
          },
      ext_modules = ext_modules,
      install_requires=['pypytools'])
