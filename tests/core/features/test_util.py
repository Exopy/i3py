# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tests for the tools to customize feature and help in their writings.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import pytest

from i3py.core.features.factories import constant, conditional
from ..testing_tools import DummyParent


def test_constant():
    """Test creating a constant getter.

    """
    builder = constant(True)
    f = builder.build_getter()
    assert f(None, None) is True


def test_conditional_getter():
    """Test creating a conditional setter.

    """
    dummy = DummyParent()
    dummy.state = False

    # not using default
    builder = conditional('1 if driver.state else 2')
    f = builder.build_getter()
    assert f(None, dummy) == 2
    assert not dummy.d_get_cmd
    dummy.state = True
    assert f(None, dummy) == 1
    assert not dummy.d_get_cmd

    # using default
    builder = conditional('1 if driver.state else 2', default=True)
    f = builder.build_getter()
    assert f(None, dummy) == 1
    assert dummy.d_get_cmd == 1
    dummy.state = False
    assert f(None, dummy) == 2
    assert dummy.d_get_cmd == 2


def test_conditional_setter():
    """Test creating a conditional setter.

    """
    dummy = DummyParent()
    dummy.state = True

    builder = conditional('1 if driver.state else 2')
    with pytest.raises(ValueError):
        builder.build_setter()

    builder = conditional('"test" if driver.state else "bis"', True)
    f = builder.build_setter()
    f(None, dummy, 1)
    assert dummy.d_set_cmd == "test"
    dummy.state = False
    f(None, dummy, 1)
    assert dummy.d_set_cmd == "bis"
