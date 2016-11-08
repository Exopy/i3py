# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Implements the Action class used to wrap public driver methods.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from functools import update_wrapper, partial

from future.utils import raise_from, exec_, with_metaclass
from past.builtins import basestring
from funcsigs import signature

from ..errors import I3pyFailedCall
from ..abstracts import AbstractAction
from ..composition import SupportMethodCustomization
from ..limits import IntLimitsValidator, FloatLimitsValidator
from ..unit import UNIT_SUPPORT, UNIT_RETURN, get_unit_registry, to_float
from ..util import (build_checker, validate_in, validate_limits,
                    get_limits_and_validate)


CALL_TEMPLATE =\
"""def __call__(self{sig}):
    try:
        params = self.action.sig.bind(self.driver{sig})
        args = params.args
        kwargs = params.kwargs
        args, kwargs = self.action.pre_call(self.driver, *args, **kargs)
        res = self.action.call(self.driver, *args, **kwargs)
        return self.action.post_call(self.driver, res, *args, **kwargs)
    except Exception as e:
        msg = ('An exception occurred while calling {} with the following '
               'arguments {} and keywords arguments.')
        raise_from(I3pyFailedCall(msg.format(self.action.name, args, kwargs)))
"""


class MetaActionCall(type):
    """Metaclass for action call object offering custom instantiation.

    """
    def __init__(cls):
        cls.sigs = {}  # Dict storing custom class for each signature

    def __call__(cls, action, driver):
        """Create a custom subclass for each signature action.

        Parameters
        ----------
        action : Action
            Action for which to return a callable.

        driver :
            Instance of the owner class of the action.

        """
        if action.sig not in cls.sigs:
            cls.sigs[action.sig] = cls.create_callable(action)

        custom_type = cls.sigs[action.sig]
        return super(MetaActionCall, custom_type)(action, driver)

    def create_callable(cls, action):
        """Dynamically create a subclass of ActionCall for a signature.

        """
        name = '{}ActionCall'.format(action.name)
        sig = action.sig
        # Should store sig on class attribute
        decl = ('class {name}(ActionCall):\n' +
                CALL_TEMPLATE
                ).format(name=name, sig=', ' + ', '.join(*sig) if sig else '')
        glob = dict(ActionCall=ActionCall, raise_from=raise_from,
                    I3pyFailedCall=I3pyFailedCall)
        exec_(decl, glob)
        return glob[name]


class ActionCall(with_metaclass(MetaActionCall, object)):
    """Object returned when an Action is used as descriptor.

    Actually when an Action is used to decorate a function a custom subclass
    of this class is created with a __call_ method whose signature match the
    decorated function signature.

    """
    __slots__ = ('action', 'driver')

    def __init__(self, action, driver):
        self.action = action
        self.driver = driver


class Action(AbstractAction, SupportMethodCustomization):
    """Wraps a method with pre and post processing operations.

    All parameters must be passed as keyword arguments.

    All public driver methods should be decorated as an Action to make them
    easy to identify and hence make instrospection easier.

    Parameters
    ----------
    units : tuple, optional
        Tuple of length 2 containing the return unit and the unit of each
        passed argument. None can be used to mark that an argument should not
        be converted. The first argument (self) should always be marked this
        way.

    checks : unicode, optional
        Booelan tests to execute before calling the function. Multiple
        assertions can be separated with ';'. All the methods argument are
        available in the assertion execution namespace so one can access to the
        driver using self and to the arguments using their name (the signature
        of the wrapper is made to match the signature of the wrapped method).

    values : dict, optional
        Dictionary mapping the arguments names to their allowed values.

    limits : dict, optional
        Dictionary mapping the arguments names to their allowed limits. Limits
        can a be a tuple of length 2, or 3 (min, max, step) or the name of
        the limits to use to check the input.

    Notes
    -----
    A single argument should be value checked or limit checked but not both,
    unit conversion is performed before anything else. When limit validating
    against a driver limits the parameter should ALWAYS be converted to the
    same unit as the one used by the limits.

    """
    def __init__(self, **kwargs):

        self.creation_kwargs = kwargs

    def __call__(self, func):
        if self.func:
            msg = 'Attempt to decorate a second function using one Action.'
            raise RuntimeError(msg)
        update_wrapper(self.__call__, func)
        self.sig = signature(func)
        self.func = func
        self.customize_call(func, self.creation_kwargs)
        return self

    def __get__(self, obj, objtype=None):
        if objtype is None:
            return self
        if self._desc is None:
            # A specialized class matching the wrapped function signature is
            # created on the fly.
            self._desc = ActionCall(self, obj)
        return self._desc

    def pre_call(self, driver, *args, **kwargs):
        """Method called before calling the decorated function.

        This method can be used to validate or modify the arguments passed
        to the function.

        Parameters
        ----------
        driver :
            Reference to the instance of the owner class for this action
            calling it.

        *args :
            Positional arguments of the function.

        **kwargs :
            Keywords arguments of the function.

        Returns
        -------
        args : tuple
            Modified (or not) positional arguments

        kwargs : dict
            Modified or not keyword arguments.

        Notes
        -----
        When customizing through composition the method used can be given
        either the above signature or the signature of the function used in the
        Action.

        """
        return args, kwargs

    def post_call(self, driver, result, *args, **kwargs):
        """Method called after calling the decorated function.

        This method can be used to alter the returned function.

        Parameters
        ----------
        driver :
            Reference to the instance of the owner class for this action
            calling it.

        result :
            Object returned by the decorated function.

        *args :
            Positional arguments of the function.

        **kwargs :
            Keywords arguments of the function.

        Returns
        -------
        result : object
            Modified (or not) result from the decorated function.

        Notes
        -----
        When customizing through composition the method used can be given
        either the above signature or the signature of the function used in the
        Action with the result added after the reference to the driver and
        before the other function arguments.

        """
        return result

    def customize_call(self, func, kwargs):
        """Store the function in call attributes and customize pre/post based
        on the kwargs.

        """
        self.call = func

        if 'limits' in kwargs or 'values' in kwargs:
            self.add_values_limits_validation(func, kwargs.get('values', {}),
                                              kwargs.get('limits', {}))

        if 'checks' in kwargs:
            self.add_checks(func, kwargs['checks'])

        if UNIT_SUPPORT and 'units' in kwargs:
            self.add_unit_support(func, kwargs['units'])

    # XXX add methods required by SupportMethodCustomization
    def analyse_function(self, meth_name, func, specifiers):
        """Analyse the possibility to use a function for a method.

        Parameters
        ----------
        meth_name : unicode
            Name of the method that should be customized using the provided
            function.

        func : callable
            Function to use to customize the method.

        specifiers : tuple
            Tuple describing the attempted modification.

        Returns
        -------
        signatures : list
            List of signatures that should be supported by a composer.

        chain_on : unicode
            Comma separated list of functions arguments that are also values
            returned by the function.

        Raises
        ------
        ValueError :
            Raised if the signature of the provided function does not match the
            one of the customized method.

        """
        # Call can be replaced only
        # pre/post support customization but the basic version can be
        # replaced as it is useless.
        pass

    @property
    def self_alias(self):
        """Name used instead of self in function signature.

        """
        return 'action'

    # XXX use modify behavior on pre_call and post_call
    # XXX need to dynamically create pre_call, call, and post_call
    #     with the right signature and custom ActionCall object
    def add_unit_support(self, func, units):
        """Wrap a func using Pint to automatically convert Quantity.

        """
        ureg = get_unit_registry()
        func = ureg.wraps(*units, strict=False)(func)
        if not UNIT_RETURN:
            def wrapper(*args, **kwargs):
                res = func(*args, **kwargs)
                return to_float(res) if res is not None else res

            update_wrapper(wrapper, func)
            return wrapper

        return func

    def add_checks(self, func, checks):
        """Build a checker function and use it to decorate func.

        Parameters
        ----------
        func : callable
            Function to decorate.

        checks : unicode
            ; separated string of expression to assert.

        Returns
        -------
        wrapped : callable
            Function wrapped with the assertion checks.

        """
        check = build_checker(checks, self.sig)

        def check_wrapper(*args, **kwargs):
            check(*args, **kwargs)
            return func(*args, **kwargs)
        update_wrapper(check_wrapper, func)
        return check_wrapper

    def add_values_limits_validation(self, func, values, limits):
        """Add arguments validation to call.

        Parameters
        ----------
        func : callable
            Function to decorate.

        values : dict
            Dictionary mapping the parameters name to the set of allowed
            values.

        limits : dict
            Dictionary mapping the parameters name to the limits they must
            abide by.

        units : dict
            Dictionary mapping

        Returns
        -------
        wrapped : callable
            Function wrapped with the parameters validation.

        """
        validators = {}
        for name, vals in values.items():
            validators[name] = partial(validate_in, name=name,
                                       values=set(vals))

        for name, lims in limits.items():
            if name in validators:
                msg = 'Arg %s can be limits or values validated not both'
                raise ValueError(msg % name)
            if isinstance(lims, (list, tuple)):
                if any([isinstance(e, float) for e in lims]):
                    l = FloatLimitsValidator(*lims)
                else:
                    l = IntLimitsValidator(*lims)

                validators[name] = partial(validate_limits, limits=l,
                                           name=name)

            elif isinstance(lims, basestring):
                validators[name] = partial(get_limits_and_validate,
                                           limits=lims, name=name)

            else:
                msg = 'Invalid type for limits values (key {}) : {}'
                raise TypeError(msg.format(name, type(lims)))

        sig = self.sig

        def wrapper(*args, **kwargs):

            bound = sig.bind(*args, **kwargs).arguments
            driver = args[0]
            for n in validators:
                validators[n](driver, bound[n])

            return func(*args, **kwargs)

        update_wrapper(wrapper, func)
        return wrapper
