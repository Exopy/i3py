# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing the unit utility functions.

"""
from pytest import raises, yield_fixture, mark

from i3py.core import unit
from i3py.core.unit import (set_unit_registry, get_unit_registry,
                            to_float, to_quantity)

try:
    from pint import UnitRegistry
except ImportError:
    pass


@yield_fixture
def teardown():
    unit.UNIT_RETURN = True
    unit.UNIT_REGISTRY = None
    yield
    unit.UNIT_REGISTRY = None
    unit.UNIT_RETURN = False


@mark.skipif(unit.UNIT_SUPPORT is False, reason="Requires Pint")
def test_set_unit_registry(teardown):
    ureg = UnitRegistry()
    set_unit_registry(ureg, False)

    assert get_unit_registry() is ureg
    assert not unit.UNIT_RETURN


@mark.skipif(unit.UNIT_SUPPORT is False, reason="Requires Pint")
def test_reset_unit_registry(teardown):
    ureg = UnitRegistry()
    set_unit_registry(ureg)
    assert unit.UNIT_RETURN
    with raises(ValueError):
        set_unit_registry(ureg)


def test_converters(teardown):
    """Test to_quantity and to_float utility functions.

    """
    val = 1.0
    assert to_float(val) == val
    assert to_float(to_quantity(val, 'A')) == val
