# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Implements the Action class used to wrap public driver methods.

"""
from functools import partial, update_wrapper
from inspect import Signature, currentframe, signature
from typing import (Any, Callable, ClassVar, Dict, List, Optional, Tuple, Type,
                    Union)

from ..abstracts import AbstractAction, AbstractHasFeatures
from ..composition import SupportMethodCustomization, normalize_signature
from ..errors import I3pyFailedCall
from ..limits import FloatLimitsValidator, IntLimitsValidator
from ..unit import UNIT_RETURN, UNIT_SUPPORT, get_unit_registry
from ..utils import (build_checker, check_options, get_limits_and_validate,
                     update_function_lineno, validate_in, validate_limits)

LINENO = currentframe().f_lineno

CALL_TEMPLATE = ("""
    def __call__(self{sig}):
        should_lock = self.action.should_lock
        if should_lock:
            self.driver.lock.acquire()
        try:
            params = self.action.sig.bind(self.driver{sig})
            args = params.args[1:]
            kwargs = params.kwargs
            args, kwargs = self.action.pre_call(self.driver, *args, **kwargs)
            res = self.action.call(self.driver, *args, **kwargs)
            return self.action.post_call(self.driver, res, *args, **kwargs)
        except Exception as e:
            msg = ('An exception occurred while calling {msg} with the '
                   'following arguments {msg} and keywords arguments {msg}.')
            fmt_msg = msg.format(self.action.name, (self.driver,) + args,
                                 kwargs)
            raise I3pyFailedCall(fmt_msg) from e
        finally:
            if should_lock:
                self.driver.lock.release()
""")


def add_retries(func, action):
    """Re-call if the call fail due to a communication issue.

    """
    def wrapper(driver, *args, **kwargs):
        i = -1
        while i < action._retries:
            try:
                i += 1
                return action.func(driver, *args, **kwargs)
            except driver.retries_exceptions:
                if i != action._retries:
                    driver.reopen_connection()
                    continue
                else:
                    raise

    update_wrapper(wrapper, func)
    return wrapper


class ActionCall(object):
    """Object returned when an Action is used as descriptor.

    Actually when an Action is used to decorate a function a custom subclass
    of this class is created with a __call__ method whose signature match the
    decorated function signature.

    """
    __slots__ = ('action', 'driver')

    #: Dict storing custom class for each signature
    sigs: Dict[Tuple[str, ...], Type['ActionCall']] = {}

    def __new__(cls, action: AbstractAction, driver: AbstractHasFeatures
                ) -> 'ActionCall':
        """Create a custom subclass for each signature action.

        Parameters
        ----------
        action : Action
            Action for which to return a callable.

        driver :
            Instance of the owner class of the action.

        """
        sig = normalize_signature(action.sig, alias='driver')
        if sig not in cls.sigs:
            cls.sigs[sig] = cls.create_callable(action, sig)

        custom_type = cls.sigs[sig]
        return object.__new__(custom_type)

    def __call__(self, *args, **kwargs):
        """Updated in subclasses to preserve the decorated function signature.

        """
        raise NotImplementedError

    @classmethod
    def create_callable(cls, action: AbstractAction, sig: Tuple[str, ...]
                        ) -> Type['ActionCall']:
        """Dynamically create a subclass of ActionCall for a signature.

        """
        name = '{}ActionCall'.format(action.name)
        # Should store sig on class attribute
        decl = ('class {name}(ActionCall):\n' +
                CALL_TEMPLATE
                ).format(msg='{}', name=name,
                         sig=', ' + ', '.join(sig[1:]))
        glob = dict(ActionCall=ActionCall,
                    I3pyFailedCall=I3pyFailedCall)

        # Consider that this file is the source of the function
        code = compile(decl, __file__, 'exec')
        exec(code, glob)
        action_call_cls: Type[ActionCall] = glob[name]

        # Set the lineno to point to the string source.
        update_function_lineno(action_call_cls.__call__, LINENO + 3)

        return action_call_cls

    def __init__(self, action: AbstractAction, driver: AbstractHasFeatures
                 ) -> None:
        self.action = action
        self.driver = driver


class BaseAction(SupportMethodCustomization):
    """Wraps a method with pre and post processing operations.

    """
    #: Class variable used to stored the king of method wrapper generated by
    #: the descriptor.
    ACTION_CALL_CLS: ClassVar[type] = ActionCall

    def __init__(self, **kwargs):
        super().__init__()
        self.name: str = ''
        self.func: Optional[Callable] = None
        self.sig: Optional[Signature] = None
        self.creation_kwargs: dict = kwargs
        self.should_lock = kwargs.get('lock', False)
        self._desc: Optional[ActionCall] = None
        self._retries: int = kwargs.get('retries', 0)
        self._use_options = bool(kwargs.get('options', False))

    def __call__(self, func: Callable) -> 'BaseAction':
        if self.func:
            msg = 'Attempt to decorate a second function using one Action.'
            raise RuntimeError(msg)
        self.__doc__ = func.__doc__
        self.sig = signature(func)
        self.func = func
        self.name = self.__name__ = func.__name__
        self.customize_call(func, self.creation_kwargs)
        return self

    def __get__(self,
                obj: AbstractHasFeatures,
                objtype: Optional[Type[AbstractHasFeatures]]=None
                ) -> Union[ActionCall, 'BaseAction']:
        if obj is None:
            return self

        if self._use_options is True:
            op, msg = obj._settings[self.name]['_options']
            if op is None:
                op, msg = check_options(obj, self.creation_kwargs['options'])
                obj._settings[self.name]['_options'] = op

            if not op:
                raise AttributeError('Invalid options: %s' % msg)

        if self._desc is None:
            # A specialized class matching the wrapped function signature is
            # created on the fly.
            self._desc = self.ACTION_CALL_CLS(self, obj)
        return self._desc

    def clone(self) -> 'BaseAction':
        """Create a clone of itself.

        """
        new = type(self)(**self.creation_kwargs)
        new(self.func)
        new.copy_custom_behaviors(self)
        new.__doc__ = self.__doc__
        new.name = self.name
        return new

    def create_default_settings(self) -> Dict[str, Any]:
        """Create the default settings for an action.

        """
        settings = {}
        if self._use_options:
            settings['_options'] = (None, '')
        return settings

    def pre_call(self, driver: AbstractHasFeatures, *args, **kwargs
                 ) -> Tuple[tuple, Dict[str, Any]]:
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

    def post_call(self, driver: AbstractHasFeatures, result: Any,
                  *args, **kwargs) -> Any:
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

    def customize_call(self, func: Callable, kwargs: Dict[str, Any]):
        """Store the function in call attributes.

        """
        if self._retries:
            func = add_retries(func, self)
        self.call = func

        if 'checks' in kwargs:
            sig = normalize_signature(self.sig, alias='driver')
            check_sig = ('(action' +
                         (', ' + ', '.join(sig) if sig else '') + ')')
            check_args = build_checker(kwargs['checks'], check_sig)

            def checker_wrapper(action, driver, *args, **kwargs):
                check_args(action, driver, *args, **kwargs)
                return args, kwargs

            self.modify_behavior('pre_call', checker_wrapper,
                                 ('append',), 'checks', internal=True)

    def analyse_function(self,
                         meth_name: str,
                         func: Callable,
                         specifiers: Tuple[str, ...]
                         ) -> Tuple[Tuple[str, ...],
                                    List[Tuple[str, ...]],
                                    str]:
        """Analyse the possibility to use a function for a method.

        Parameters
        ----------
        meth_name : str
            Name of the method that should be customized using the provided
            function.

        func : callable
            Function to use to customize the method.

        specifiers : tuple
            Tuple describing the attempted modification.

        Returns
        -------
        specifiers : tuple
            Tuple describing a possibly simplified customization that the one
            suggested by the user.

        signatures : list
            List of signatures that should be supported by a composer.

        chain_on : str
            Comma separated list of functions arguments that are also values
            returned by the function.

        Raises
        ------
        ValueError :
            Raised if the signature of the provided function does not match the
            one of the customized method.

        """
        act_sig = ('action',) + normalize_signature(self.sig,
                                                    alias=self.self_alias)

        if meth_name == 'call':
            if specifiers:
                msg = ('Can only replace call method of an action, not '
                       'customize it. Failed on action {} with customization '
                       'specifications {}')
                raise ValueError(msg.format(self.name, specifiers))
            sigs = [act_sig]
            chain_on = None

        elif meth_name == 'pre_call':
            sigs = [('action', 'driver', '*args', '**kwargs'), act_sig]
            chain_on = 'args, kwargs'
            # The base version of pre_call is no-op so we can directly replace
            if self.pre_call.__func__ is Action.pre_call:
                specifiers = ()

        elif meth_name == 'post_call':
            sigs = [('action', 'driver', 'result', '*args', '**kwargs'),
                    ('action', 'driver', 'result') + act_sig[2:]]
            chain_on = 'result'
            # The base version of post_call is no-op so we can directly replace
            if self.post_call.__func__ is Action.post_call:
                specifiers = ()

        else:
            msg = ('Cannot customize method {}, only pre_call, call and '
                   'post_call can be.')
            raise ValueError(msg)

        func_sig = normalize_signature(signature(func), self.self_alias)

        if func_sig not in sigs:
            msg = ('Function {} used to attempt to customize method {} of '
                   'action {} does not have the right signature '
                   '(expected={}, provided={}).')
            raise ValueError(msg.format(func.__name__, meth_name, self.name,
                                        sigs, func_sig))

        return specifiers, sigs, chain_on

    @property
    def self_alias(self) -> str:
        """Name used instead of self in function signature.

        """
        return 'driver'


AbstractAction.register(BaseAction)


class Action(BaseAction):
    """Wraps a method with pre and post processing operations.

    All parameters must be passed as keyword arguments.

    All public driver methods should be decorated as an Action to make them
    easy to identify and hence make introspection easier.

    Parameters
    ----------
    options : str, optional
        Assertions in the form option_name['option_field'] == possible_values
        or any other valid boolean test. Multiple assertions can be separated
        by ;

    checks : str, optional
        Boolean tests to execute before calling the function. Multiple
        assertions can be separated with ';'. All the method arguments are
        available in the assertion execution namespace so one can access to the
        driver using self and to the arguments using their name (the signature
        of the wrapper is made to match the signature of the wrapped method).

    values : dict, optional
        Dictionary mapping the arguments names to their allowed values.

    limits : dict, optional
        Dictionary mapping the arguments names to their allowed limits. Limits
        can a be a tuple of length 2, or 3 (min, max, step) or the name of
        the limits to use to check the input.

    units : tuple, optional
        Tuple of length 2 containing the return unit and the unit of each
        passed argument. None can be used to mark that an argument should not
        be converted. The first argument (self) should always be marked this
        way.

    retries: int, optional
        Number of times to re-attempt to call the decoarated function if an
        exception listed in the driver `retries_exception` occurs.

    Notes
    -----
    A single argument should be value checked or limit checked but not both,
    unit conversion is performed before anything else. When limit validating
    against a driver limits the parameter should ALWAYS be converted to the
    same unit as the one used by the limits.

    """
    def create_default_settings(self) -> Dict[str, Any]:
        """Create the default settings for an action.

        """
        settings = super().create_default_settings()
        settings['unit_return'] = UNIT_RETURN
        return settings

    def customize_call(self, func: Callable, kwargs: Dict[str, Any]):
        """Store the function in call attributes and customize pre/post based
        on the kwargs.

        """
        super().customize_call(func, kwargs)
        if 'limits' in kwargs or 'values' in kwargs:
            self.add_values_limits_validation(kwargs.get('values', {}),
                                              kwargs.get('limits', {}))

        if UNIT_SUPPORT and 'units' in kwargs:
            self.add_unit_support(kwargs['units'])

    def add_unit_support(self, units: Tuple[str, Dict[str, Optional[str]]]):
        """Wrap a func using Pint to automatically convert Quantity to float.

        """
        ureg = get_unit_registry()
        if len(units[1]) != len(self.sig.parameters):
            msg = ('The number of provided units does not match the number of '
                   'function arguments.')
            raise ValueError(msg)

        def convert_input(action, driver, *args, **kwargs):
            """Convert the arguments to the proper unit and return magnitudes.

            """
            bound = self.sig.bind(driver, *args, **kwargs)
            for i, (k, v) in enumerate(list(bound.arguments.items())):
                if units[1][i] is not None and isinstance(v, ureg.Quantity):
                    bound.arguments[k] = v.to(units[1][i]).m

            # remove driver from the args
            return bound.args[1:], bound.kwargs

        self.modify_behavior('pre_call', convert_input, ('prepend',), 'units',
                             internal=True)

        def convert_output(action, driver, result, *args, **kwargs):
            """Convert the output to the proper units.

            """
            if not driver._settings[self.name]['unit_return']:
                return result
            re_units = units[0]
            is_container = isinstance(re_units, (tuple, list))
            if not is_container:
                result = [result]
                re_units = [re_units]

            results = [ureg.Quantity(result[i], u)
                       for i, u in enumerate(re_units)]

            return results if is_container else results[0]

        self.modify_behavior('post_call', convert_output, ('append',), 'units',
                             internal=True)

    def add_values_limits_validation(self, values: Dict[str, tuple],
                                     limits: Dict[str, Union[str, list, tuple]]
                                     ):
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
                    lim = FloatLimitsValidator(*lims)
                else:
                    lim = IntLimitsValidator(*lims)  # type: ignore

                validators[name] = partial(validate_limits, limits=lim,
                                           name=name)

            elif isinstance(lims, str):
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

            return args, kwargs

        self.modify_behavior('pre_call', validate_args, ('append',),
                             'values_limits', internal=True)
