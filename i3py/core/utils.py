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
from types import CodeType
from inspect import currentframe
from pprint import pformat
from collections import OrderedDict

from .errors import I3pyValueError, I3pyLimitsError
from .abstracts import AbstractBaseDriver, AbstractOptions


def update_function_lineno(func, lineno):
    """Update the co_lineno of the code object of a function.

    """
    fcode = func.__code__
    func.__code__ = CodeType(fcode.co_argcount, fcode.co_kwonlyargcount,
                             fcode.co_nlocals, fcode.co_stacksize,
                             fcode.co_flags, fcode.co_code,
                             fcode.co_consts, fcode.co_names,
                             fcode.co_varnames, fcode.co_filename,
                             fcode.co_name, lineno, fcode.co_lnotab,
                             fcode.co_freevars, fcode.co_cellvars)
    return func


# TODO use AST analysis to provide more infos about assertion
# failure. Take inspiration from pytest.assertions.rewrite.
def report_on_assertion_error(assertion, namespace):
    """Build a string explaining why an assertion failed.

    The explanantion is built from the string representing the assertion and
    the namespace in which the assertion was evaluated.

    """
    return f'Assertion {assertion} failed when evaluated with {namespace}'


LINENO = currentframe().f_lineno

CHECKER_TEMPLATE = """
def check{signature}:
    for a_str, a_code in assertions.items():
        assert eval(a_code), report_on_assertion_error(a_str, locals())
    return {ret}

"""


def build_checker(checks, signature, ret=''):
    """Assemble a checker function from the provided assertions.

    Parameters
    ----------
    checks : str
        ; separated string containing boolean test to assert.

    signature : str or inspect.Signature
        Signature of the check function to build.

    ret : str
        Name of the parameters to return. This string will be preceded by a
        return statement.

    Returns
    -------
    checker : function
        Function to use

    """
    # Closure variable for the compilation of the checker function
    assertions = {a_str.strip(): compile(a_str.strip(),
                                         '<'+a_str.strip()+'>', 'eval')
                  for a_str in checks.split(';')}
    func_def = CHECKER_TEMPLATE.format(signature=str(signature),
                                       ret=ret or 'None')
    loc = {'assertions': assertions}
    glob = globals().copy()
    glob.update(loc)
    exec(compile(func_def, __file__, 'exec'), glob, loc)

    return update_function_lineno(loc['check'], LINENO + 3)


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
            for o in [name for name, feat in d.__feats__.items()
                      if isinstance(feat, AbstractOptions)]:
                options[o] = getattr(d, o)
            if isinstance(d, AbstractBaseDriver):
                break
            else:
                d = d.parent
    else:
        options = driver_or_options

    for test in option_values.split(';'):
        # Eval add builtins to the dict hence the copy
        if not eval(test, options.copy()):
            msg = 'The following options does match {} (options are {})'
            return False, msg.format(test, pformat(options))

    return True, ''


# The next three function take all driver as first argument for homogeneity.
# This allows to use them nearly as is to modify Feature or Action

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


def register_names_from_names_and_length(names, length):
    """Create a list of names to match a bit field of given length.

    Parameters
    ----------
    names : dict | list
        Mapping between the field names and their index or list of names.
        In the case of a list its length must match length.

    length : int
        Number of fields in the bit field.

    Returns
    -------
    register_names : list
        List of names for the bit field fields. Missing are replaced by their
        index (as an int).

    """
    if isinstance(names, dict):
        aux = list(range(length))
        for n, i in names.items():
            aux[i] = n
        register_names = aux

    else:
        register_names = list(names)
        if len(names) != length:
            raise ValueError('Register necessitates %d names' % length)

        # Makes sure every key is unique by using the bit index if None is
        # found
        for i, n in enumerate(names[:]):
            register_names[i] = n or i

    return register_names


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
