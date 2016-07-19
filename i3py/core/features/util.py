# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tools to customize feature and help in their writings.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from types import MethodType
from functools import update_wrapper

from future.utils import exec_


def wrap_custom_feat_method(meth, feat):
    """ Wrap a HasFeature method to make it an driver method of a Feature.

    This is necessary so that users can define overriding method in a natural
    way in the HasFeatures subclass assuming that the driver object will be
    passed as first argument and the Feature object as second when in reality
    it will be the other way round due to python binding mechanism.

    Parameters
    ----------
    meth : MethodType
        Method which should be used to alter the default behaviour of the
        Feature.
    feat : Feature
        Instance of Feature whose default behaviour should be overridden.

    Returns
    -------
    wrapped : MethodType
        Method object which can be

    """
    # Access the real function in case a method is passed.
    if isinstance(meth, MethodType):
        if meth.__self__ is feat:
            return meth

        wrapped = meth.__func__
    else:
        wrapped = meth

    # Wrap if necessary the function to match the argument order.
    if not hasattr(meth, '_feat_wrapped_'):
        def wrapper(feat, driver, *args, **kwargs):
            return wrapped(driver, feat, *args, **kwargs)

        update_wrapper(wrapper, wrapped)
        wrapper._feat_wrapped_ = wrapped
    else:
        wrapper = wrapped

    return MethodType(wrapper, feat)


# --- Methods composers -------------------------------------------------------

class MethodsComposer(object):
    """Function like object used to compose feature methods calls.

    All methods to call are kept in an ordered dict ensuring that they will
    be called in the right order while allowing fancy insertion based on method
    id.

    Notes
    -----
    Method ids must be unique and duplicate names are removed without warning.

    """
    __slots__ = ('_names', '_methods')

    def __init__(self):
        self._methods = []
        self._names = []

    def clone(self):
        new = type(self)()
        new._names = self._names[:]
        new._methods = self._methods[:]
        return new

    def prepend(self, name, method):
        """Prepend a method to existing ones.

        Parameters
        ----------
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._remove_duplicate(name)
        self._names.insert(0, name)
        self._methods.insert(0, method)

    def append(self, name, method):
        """Append a method to existing ones.

        Parameters
        ----------
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._remove_duplicate(name)
        self._names.append(name)
        self._methods.append(method)

    def add_after(self, anchor, name, method):
        """Add the given method after a given one.

        Parameters
        ----------
        anchor : unicode
            Id of the method after which to insert the given one.
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._remove_duplicate(name)
        i = self._names.index(anchor)
        self._names.insert(i+1, name)
        self._methods.insert(i+1, method)

    def add_before(self, anchor, name, method):
        """Add the given method before the specified one.

        Parameters
        ----------
        anchor : unicode
            Id of the method before which to insert the given one.
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._remove_duplicate(name)
        i = self._names.index(anchor)
        self._names.insert(i, name)
        self._methods.insert(i, method)

    def replace(self, name, method):
        """Replace an existing method by a new one.

        Only custom methods can be replaced. Methods whose presence is
        linked to the feature kwargs cannot be replaced.

        Parameters
        ----------
        name : unicode
            Id of the method of the method to replace.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        i = self._names.index(name)
        self._methods[i] = method

    def remove(self, name):
        """Remove a method.

        Parameters
        ----------
        name : unicode
            Id of the method to remove.

        """
        i = self._names.index(name)
        del self._names[i]
        del self._methods[i]

    def reset(self):
        """Empty the composer.

        """
        self._names = []
        self._methods = []

    def __getitem__(self, key):
        return self._methods[self._names.index(key)]

    def __contains__(self, item):
        return item in self._names

    def _remove_duplicate(self, name):
        """Remove the name from the list to avoid having duplicate ids.

        """
        if name in self._names:
            i = self._names.index(name)
            del self._names[i]
            del self._methods[i]


class PreGetComposer(MethodsComposer):
    """Composer used for pre_get methods.

    """
    __slots__ = ()

    def __call__(self, driver):
        """Call mimicking a pre_get method and calling all assigned methods
        in order with the driver as only argument.

        """
        for m in self._methods:
            m(driver)


class PostGetComposer(MethodsComposer):
    """Composer for post_get methods.

    """
    __slots__ = ()

    def __call__(self, driver, value):
        """Call mimicking a post_get method and calling all assigned methods
        in order. The value returned by each method is passed to the next one.

        """
        for m in self._methods:
            value = m(driver, value)
        return value


class PreSetComposer(MethodsComposer):
    """Composer for pre_set methods.

    """
    __slots__ = ()

    def __call__(self, driver, value):
        """Call mimicking a pre_set method and calling all assigned methods
        in order. The value returned by each method is passed to the next one.

        """
        for m in self._methods:
            value = m(driver, value)
        return value


class PostSetComposer(MethodsComposer):
    """Composer for post_set methods.

    """
    __slots__ = ()

    def __call__(self, driver, value, d_value, response):
        """Call mimicking a post_set method and calling all assigned methods
        in order.

        """
        for m in self._methods:
            value = m(driver, value, d_value, response)

COMPOSERS = {'pre_get': PreGetComposer, 'post_get': PostGetComposer,
             'pre_set': PreSetComposer, 'post_set': PostSetComposer}


# --- Customisation decorators ------------------------------------------------

def append(id_str='custom'):
    """Mark a function to be appended to a MethodsComposer.

    """
    def decorator(function):
        function._composing = (id_str, 'append')
        return function

    return decorator


def prepend(id_str='custom'):
    """Mark a function to be prepended to a MethodsComposer.

    """
    def decorator(function):
        function._composing = (id_str, 'prepend')
        return function

    return decorator


def add_after(name, id_str='custom'):
    """Mark a function to be added after another in a MethodsComposer.

    """
    def decorator(function):
        function._composing = (id_str, 'add_after', name)
        return function

    return decorator


def add_before(name, id_str='custom'):
    """Mark a function to be added before another in a MethodsComposer.

    """
    def decorator(function):
        function._composing = (id_str, 'add_before', name)
        return function

    return decorator


def replace(id_str):
    """Mark a function to replace another in a MethodsComposer.

    """
    def decorator(function):
        function._composing = (id_str, 'replace')
        return function

    return decorator

# --- Getter/setter factories -------------------------------------------------


class AbstractGetSetFactory(object):
    """Abstract class for get/set factories.

    Use by Feature to identify such a factory and use it to replace the
    get/set method.

    """

    def build_getter(self):
        """Build the function for getting the Feature value.

        This method is called when a get/set factory is passed as the getter
        argument to a Feature.

        """
        raise NotImplementedError()

    def build_setter(self):
        """Build the function for setting the Feature value.

        This method is called when a get/set factory is passed as the setter
        argument to a Feature.

        """
        raise NotImplementedError()


class constant(AbstractGetSetFactory):
    """Make a Feature return always the same value.

    This can only be used as a getter factory.

    Parameters
    ----------
    value :
        The value the Feature should return

    """

    def __init__(self, value):
        super(constant, self).__init__()
        self._value = value

    def build_getter(self):
        """Build a trivial function to return the constant value.

        """
        value = self._value

        def getter(self, driver):
            return value

        return getter


GET_DEF =\
"""def get(self, driver):
    val = {}
    return {}

"""

SET_DEF =\
"""def set(self, driver, value):
    cmd = {}
    return driver.default_set_feature(self, cmd, value)
"""


class conditional(AbstractGetSetFactory):
    """Make a Feature modify getting/setting based on the driver state.

    Parameters
    ----------
    conditional_value : unicode
        String of the form 'a if driver.b else c'. When setting the value is
        accessible as value.

    default : bool
        Pass the result of the conditional evalutation to the
        default_get/set_feature method of the driver if True, otherwise
        directly return the result.
        When building a setter this MUST be true.

    """

    def __init__(self, conditional_value, default=False):
        super(conditional, self).__init__()
        self._cond = conditional_value
        self._default = default

    def build_getter(self):
        """Build the getter.

        """
        if not self._default:
            get_def = GET_DEF.format(self._cond, 'val')

        else:
            get_def = GET_DEF.format(self._cond,
                                     'driver.default_get_feature(self, val)')

        loc = {}
        exec_(get_def, globals(), loc)

        return loc['get']

    def build_setter(self):
        """Build the setter.

        """
        if not self._default:
            raise ValueError('Can build a setter only if default is True')

        loc = {}
        exec_(SET_DEF.format(self._cond), globals(), loc)

        return loc['set']
