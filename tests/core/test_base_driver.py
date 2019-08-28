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
from pytest import raises, fixture

from i3py.core.base_driver import BaseDriver


@fixture
def base_version():
    BaseDriver.__version__ = '0.1.0'


def test_bdriver_multiple_creation(base_version):
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


def test_driver_enforce_version():
    """Test that properly validate the presence of a __version__ attr.

    """
    del BaseDriver.__version__
    assert "__version__" not in dir(BaseDriver)
    with raises(AttributeError) as excinfo:
        class A(BaseDriver):
            pass
        A()

    assert "__version__" in str(excinfo.value)

    class A(BaseDriver):
        __version__ = "0.0.1"

    with raises(AttributeError) as excinfo:
        class B(A):
            pass
        B()

    assert "__version__" in str(excinfo.value)


def test_bdriver_initiliaze(base_version):
    with raises(NotImplementedError):
        BaseDriver(a=1).initialize()


def test_bdriver_finalize(base_version):
    with raises(NotImplementedError):
        BaseDriver(a=1).finalize()


def test_bdriver_check(base_version):
    assert not BaseDriver(a=1).check_connection()


def test_bdriver_connected(base_version):
    with raises(NotImplementedError):
        BaseDriver(a=1).is_connected()


def test_bdriver_context(base_version):

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
