# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test base driver functionalities.

"""
from pytest import raises

from i3py.core.base_driver import BaseDriver

BaseDriver.__version__ = '0.1.0'


def test_bdriver_multiple_creation():
    a = BaseDriver(a=1)
    assert hasattr(a, 'owner') is True
    assert hasattr(a, 'lock') is True
    assert a.newly_created is True
    b = BaseDriver(a=1)
    assert a is b
    assert b.newly_created is False

    class Aux(BaseDriver):

        __version__ = '0.2.0'

    c = Aux(a=1)
    assert c is not b


def test_bdriver_initiliaze():
    with raises(NotImplementedError):
        BaseDriver(a=1).initialize()


def test_bdriver_finalize():
    with raises(NotImplementedError):
        BaseDriver(a=1).finalize()


def test_bdriver_check():
    assert not BaseDriver(a=1).check_connection()


def test_bdriver_connected():
    with raises(NotImplementedError):
        BaseDriver(a=1).connected


def test_bdriver_context():

    class Driver(BaseDriver):

        __version__ = '0.2.0'

        def initialize(self):
            self._c = True

        def finalize(self):
            self._c = False

        @property
        def connected(self):
            return self._c

    with Driver() as d:
        assert d.connected
