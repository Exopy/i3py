#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import os.path
import sys

sys.path.insert(0, os.path.abspath('.'))
from ecpy.version import __version__

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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        ],
    zip_safe=False,
    packages=find_packages(exclude=['tests', 'tests.*']),
    package_data={'': ['*.yaml']},
    requires=['future', 'pyqt4', 'atom', 'enaml', 'kiwisolver', 'configobj',
              'watchdog', 'setuptools', 'qtawesome'],
    install_requires = ['future', 'funcsigs', 'stringparser'],
    requires = ['future', 'pyvisa', 'funcsigs', 'stringparser'],
)
