#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import os.path
import sys

sys.path.insert(0, os.path.abspath('.'))
from i3py.version import __version__

setup(
    name='i3py',
    description='Instrument interfacing in Python',
    version=__version__,
    long_description='',
    author='I3py Developers (see AUTHORS)',
    author_email='m.dartiailh@gmail.com',
    url='http://github.com/ecpy/i3py',
    download_url='http://github.com/ecpy/i3py/tarball/master',
    keywords='instrument interfacing Python',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: Physics',
        'Programming Language :: Python :: 3.6',
        ],
    zip_safe=False,
    packages=find_packages(exclude=['tests', 'tests.*']),
    requires=['stringparser'],
    install_requires=['stringparser'],
)
