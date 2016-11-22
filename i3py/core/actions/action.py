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

from inspect import cleandoc
from functools import partial

from future.utils import raise_from, exec_, with_metaclass
from past.builtins import basestring
from funcsigs import signature

from ..errors import I3pyFailedCall
from ..abstracts import AbstractAction
from ..composition import SupportMethodCustomization, normalize_signature
from ..limits import IntLimitsValidator, FloatLimitsValidator
from ..unit import UNIT_SUPPORT, UNIT_RETURN, get_unit_registry
from ..util import (build_checker, validate_in, validate_limits,
                    get_limits_and_validate)


CALL_TEMPLATE = cleandoc("""
def __call__(self{sig}):
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
""")


class MetaActionCall(type):
    """Metaclass for action call object offering custom instantiation.

    """
    #: Dict storing custom class for each signature
    sigs = {}

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
        sig = normalize_signature(action.sig)
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
        super(Action, self).__init__()
        self.name = ''
        self.func = None
        self.creation_kwargs = kwargs

    def __call__(self, func):
        if self.func:
            msg = 'Attempt to decorate a second function using one Action.'
            raise RuntimeError(msg)
        self.__doc__ = func.__doc__
        self.sig = signature(func)
        self.func = func
        self.name = func.__name__
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
            sig = normalize_signature(self.sig, alias='driver')
            check_sig = ('(action' +
                         (', ' + ', '.join(sig) if sig else '') + ')')
            check_args = build_checker(kwargs['checks'], check_sig)
            self.modify_behavior('pre_call', check_args,
                                 ('append',), 'checks', internal=True)

        if UNIT_SUPPORT and 'units' in kwargs:
            self.add_unit_support(func, kwargs['units'])

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
        func_sig = normalize_signature(signature(func), self.self_alias)

        if meth_name == 'call':
            if specifiers:
                msg = ('Can only replace call method of an action, not '
                       'customize it. Failed on action {} with customization '
                       'specifications {}')
                raise ValueError(msg.format(self.name, specifiers))
            sigs = [func_sig]
            chain_on = None

        elif meth_name == 'pre_call':
            sigs = [func_sig, ('action', 'driver', '*args', '**kwargs')]
            chain_on = 'args, kwargs'
            # The base version of pre_call is no-op so we can directly replace
            # Python 2/3 compatibility hack.
            original = getattr(Action.pre_call, '__func__', Action.pre_call)
            if self.pre_call.__func__ is original:
                specifiers = ()

        elif meth_name == 'post_call':
            sigs = [('action', 'driver', 'result') + func_sig[2:],
                    ('action', 'driver', 'result', '*args', '**kwargs')]
            chain_on = 'result'
            # The base version of post_call is no-op so we can directly replace
            original = getattr(Action.post_call, '__func__', Action.post_call)
            if self.post_call.__func__ is original:
                specifiers = ()

        else:
            msg = ('Cannot cutomize method {}, only pre_call, call and '
                   'post_call can be.')
            raise ValueError(msg)

        if func_sig not in sigs:
            msg = ('Function {} used to attempt to customize method {} of '
                   'action {} does not have the right signature '
                   '(expected={}, provided={}).')
            raise ValueError(msg.format(func.__name__, meth_name, self.name,
                                        sigs, func_sig))

        return specifiers, sigs, chain_on

    @property
    def self_alias(self):
        """Name used instead of self in function signature.

        """
        return 'action'

    def add_unit_support(self, units):
        """Wrap a func using Pint to automatically convert Quantity to float.

        """
        ureg = get_unit_registry()
        if len(units[1]) != len(self.sig.parameters):
            msg = ''
            raise ValueError(msg)

        def convert_input(action, driver, *args, **kwargs):
            """Convert the arguments to the proper unit and return magnitudes.

            """
            bound = self.sig.bind(driver, *args, **kwargs)
            for i, (k, v) in enumerate(list(bound.parameters.items())):
                if units[1][i] is not None and isinstance(v, ureg.Quantity):
                    bound.parameters[k] = v.to(units[1][i]).m

            return bound.args, bound.kwargs

        self.modify_behavior('pre_call', convert_input, ('prepend',), 'units',
                             internal=True)

        if not UNIT_RETURN:
            return

        def convert_output(action, driver, result, *args, **kwargs):
            """Convert the output to the proper units.

            """
            re_units = units[0]
            is_container = isinstance(re_units, (tuple, list))
            if not is_container:
                result = [result]
                re_units = [re_units]

            results = [ureg.Quantity(result[i], u)
                       for i, u in enumerate(units)]

            return results if is_container else results[0]

        self.modify_behavior('post_call', convert_output, ('append',), 'units',
                             internal=True)

    def add_values_limits_validation(self, values, limits):
        """Add arguments validation to pre_call.

        Parameters
        ----------
        values : dict
            Dictionary mapping the parameters name to the set of allowed
            values.

        limits : dict
            Dictionary mapping the parameters name to the limits they must
            abide by.

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

        def validate_args(action, driver, *args, **kwargs):

            bound = sig.bind(driver, *args, **kwargs).arguments
            for n in validators:
                validators[n](driver, bound[n])

        self.modify_behavior('pre_call', validate_args, ('append',),
                             'values_limits', internal=True)
