# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing action behavior.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from pytest import mark, raises

from i3py.core.actions import Action
from i3py.core.limits import IntLimitsValidator
from i3py.core.unit import UNIT_SUPPORT, get_unit_registry
from ..testing_tools import DummyParent


def test_naked_action():
    """Test defining a simple action.

    """
    class Dummy(DummyParent):

        @Action()
        def test(self):
            return type(self)

    assert isinstance(Dummy.test, Action)

    dummy = Dummy()
    assert dummy.test() is Dummy


def test_values_action():
    """Test defining an action with values validation.

    """
    class Dummy(DummyParent):

        @Action(values={'a': (1, 2, 3)})
        def test(self, a, b):
            return a * b

    dummy = Dummy()
    assert dummy.test(1, 5) == 5
    with raises(ValueError):
        dummy.test(5, 2)


def test_limits_action1():
    """Test defining an action with integer limits validation.

    """
    class Dummy(DummyParent):

        @Action(limits={'b': (1, 10, 2)})
        def test(self, a, b):
            return a

    dummy = Dummy()
    assert dummy.test(1, 1) == 1
    with raises(ValueError):
        dummy.test(2,  2)


def test_limits_action2():
    """Test defining an action with floating limits validation.

    """
    class Dummy(DummyParent):

        @Action(limits={'b': (1.0, 10.0, 0.1)})
        def test(self, a, b):
            return a

    dummy = Dummy()
    assert dummy.test(1, 1)
    with raises(ValueError):
        dummy.test(2,  1.05)


def test_limits_action3():
    """Test defining an action getting the limits from the driver.

    """
    class Dummy(DummyParent):

        @Action(limits={'b': 'c'})
        def test(self, a, b):
            return a

        def _limits_c(self):
            return IntLimitsValidator(1, 10, 2)

    dummy = Dummy()
    assert dummy.test(1, 1)
    with raises(ValueError):
        dummy.test(2,  2)


def test_limits_action4():
    """Test defining an action with the wrong type of limits.

    """
    with raises(TypeError):
        class Dummy(DummyParent):

            @Action(limits={'b': 1})
            def test(self, a, b):
                return a


def test_action_with_overlapping_limits_and_values():
    """Test defining an action validating the same parameter using values and
    limits.

    """
    with raises(ValueError):
        class Dummy(DummyParent):

            @Action(limits={'b': (1, 10, 2)}, values={'b': (1, 2, 3)})
            def test(self, a, b):
                return a


@mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
def test_action_with_unit():
    """Test defining an action using units conversions.

    """
    class Dummy(DummyParent):

        @Action(units=('ohm*A', (None, 'ohm', 'A')))
        def test(self, r, i):
            return r*i

    assert isinstance(Dummy.test, Action)

    dummy = Dummy()
    assert dummy.test(2, 3) == get_unit_registry().parse_expression('6 V')

    from i3py.core.actions import action

    try:
        action.UNIT_RETURN = False

        class Dummy(DummyParent):

            @Action(units=('ohm*A', (None, 'ohm', 'A')))
            def test(self, r, i):
                return r*i

    finally:
        action.UNIT_RETURN = True

    dummy = Dummy()

    assert dummy.test(2, 3) == 6


def test_action_with_checks():
    """Test defining an action with checks.

    """
    class Dummy(DummyParent):

        @Action(checks='r>i;i>0')
        def test(self, r, i):
            return r*i

    assert isinstance(Dummy.test, Action)

    dummy = Dummy()
    assert dummy.test(3, 2) == 6
    with raises(AssertionError):
        dummy.test(2, 2)

    with raises(AssertionError):
        dummy.test(3, -1)
