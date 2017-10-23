# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Collection of utility functions.

"""
from pprint import pformat
from collections import OrderedDict

from .errors import I3pyValueError, I3pyLimitsError
from .abstracts import AbstractBaseDriver, AbstractOptions


def build_checker(checks, signature, ret=''):
    """Assemble a checker function from the provided assertions.

    Parameters
    ----------
    checks : str
        ; separated string containing boolean test to assert.

    signature : str or funcsigs.Signature
        Signature of the check function to build.

    ret : str
        Name of the parameters to return. This string will be preceded by a
        return statement.

    Returns
    -------
    checker : function
        Function to use

    """
    func_def = 'def check' + str(signature) + ':\n'
    assertions = checks.split(';')
    for assertion in assertions:
        # TODO use AST manipulation to provide more infos about assertion
        # failure. Take inspiration from pytest.assertions.rewrite.
        a_mess = '"""Assertion %s failed"""' % assertion
        func_def += '    assert ' + assertion + ', ' + a_mess + '\n'

    if ret:
        func_def += '    return %s' % ret

    loc = {}
    exec(func_def, globals(), loc)
    return loc['check']


def check_options(driver_or_options, option_values):
    """Check that the specified options match their expected values.

    Parameters
    ----------
    driver_or_options : AbstractHasFeature or dict
        Driver from which to collect the opttions or equivalent dictionary
        with the options values (as dict of dict)

    options_values: str
        Assertions in the form option_name['option_field'] == possible_values
        or any other valid boolean test. Multiple assertions can be separated
        by ;

    """
    if not isinstance(driver_or_options, dict):
        options = {}
        d = driver_or_options
        while True:
            for o in [f for f in d.__feats__
                      if isinstance(d, AbstractOptions)]:
                options[o] = getattr(d, o)
            if isinstance(d, AbstractBaseDriver):
                break
            else:
                d = d.parent
    else:
        options = driver_or_options

    for test in option_values.split(';'):
        if not eval(test, options):
            msg = 'The following options does match %s (options are %s)'
            return False, msg % (test, pformat(options))

    return True, ''


# The next three function take all driver as first argument for homogeneity.

def validate_in(driver, value, values, name):
    """Assert that a value is in a container.

    """
    if value not in values:
        mess = 'Allowed value for {} are {}, {} not allowed'
        raise I3pyValueError(mess.format(name, values, value))
    return value


def validate_limits(driver, value, limits, name):
    """Make sure a value is in the given range.

    """
    if not limits.validate(value):
        raise_limits_error(name, value, limits)
    else:
        return value


def get_limits_and_validate(driver, value, limits, name):
    """Query the current limits from the driver and validate the values.

    """
    limits = driver.get_limits(limits)
    return validate_limits(driver, value, limits, name)


def raise_limits_error(name, value, limits):
    """Raise a value when the limits validation fails.

    """
    mess = 'The provided value {} is out of bound for {}.'
    mess = mess.format(value, name)
    if limits.minimum:
        mess += ' Minimum {}.'.format(limits.minimum)
    if limits.maximum:
        mess += ' Maximum {}.'.format(limits.maximum)
    if limits.step:
        mess += ' Step {}.'.format(limits.step)
    raise I3pyLimitsError(mess)


def byte_to_dict(byte, mapping):
    """Convert a byte to a dictionary.

    Parameters
    ----------
    byte : int
        Byte value to interpret.

    mapping : iterable
        Names to associate to each bit value. The length of the iterable should
        match the number of bit to decode.

    """
    def bit_conversion(x, i):
            return bool(x & (1 << i))

    return OrderedDict((n or i, bit_conversion(byte, i))
                       for i, n in enumerate(mapping))


def dict_to_byte(values, mapping):
    """Convert a dictionary to a byte value.

    Parameters
    ----------
    values : dict
        Dictionary whose True values will be interpreted as high bit.

    mapping : iterable
        Name to associate to each bit value. The length of the iterable should
        match the number of bit to endecode.

    """
    byte = sum((2**mapping.index(k) for k in values if values[k]))
    return byte
