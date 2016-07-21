# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
""" Unit handling is done using the Pint library.

If absent the unit support is simply disabled.

This module allows the user to specify the UnitRegistry to be used by I3py
and exposes some useful Pint features.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import logging

UNIT_SUPPORT = True
UNIT_RETURN = True

try:
    from pint import UnitRegistry
except ImportError:
    UNIT_SUPPORT = False


UNIT_REGISTRY = None


def set_unit_registry(unit_registry, return_quantity=True):
    """Set the UnitRegistry used by I3py.

    Given that conversion can only happen for units declared in the same
    UnitRegistry an application should only use a single registry. This method
    should be called before doing anything else in I3py (even importing driver)
    to avoid the creation of a default registry by I3py.

    Parameters
    ----------
    unit_registry : UnitRegistry
        UnitRegistry to use for I3py.

    return_quantity : bool, optional
        Should a Quantity object be returned when possible or a simple float.

    Raises
    ------
    ValueError:
        If a unit registry has already been set.

    """
    global UNIT_REGISTRY
    global UNIT_RETURN
    if UNIT_REGISTRY:
        mess = 'The unit registry used by I3py cannot be changed once set.'
        raise ValueError(mess)

    UNIT_REGISTRY = unit_registry
    UNIT_RETURN = return_quantity


def get_unit_registry():
    """Access the UnitRegistry currently in use by I3py.

    If no UnitRegistry has been previously declared using `set_unit_registry`,
    a new UnitRegistry  is created.

    """
    global UNIT_REGISTRY
    if not UNIT_REGISTRY:
        logger = logging.getLogger(__name__)
        logger.debug('Creating default UnitRegistry for I3py')
        UNIT_REGISTRY = UnitRegistry()

    return UNIT_REGISTRY


def to_float(value):
    """Convert a value which could be a Quantity to a float.

    """
    try:
        return value._magnitude if UNIT_SUPPORT else value
    except AttributeError:
        return value


def to_quantity(value, unit):
    """Turn a value into a Quantity with the given unit.

    This is a no-op if unit support is not available.

    Parameters
    ----------
    value : float
        Value to cast.

    unit : unicode
        Unit of the quantity to create.

    """
    if UNIT_SUPPORT:
        ureg = get_unit_registry()
        value *= ureg.parse_expression(unit)

    return value
