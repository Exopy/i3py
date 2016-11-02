# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base descriptor for all instrument properties declaration.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from types import MethodType

from stringparser import Parser

from ..errors import I3pyError
from ..util import build_checker
from ..abstracts import AbstractFeature, AbstractGetSetFactory
from ..composition import SupportMethodCustomization


class Feature(AbstractFeature, SupportMethodCustomization):
    """Descriptor representing the most basic instrument property.

    Features should not be used outside the definition of a class to avoid
    weird behaviour when some methods are customized.
    Feature are not meant to be used when writing a driver as it is a bit
    bare, one should rather use the more specialised found in other modules
    of the features package.

    When subclassing a Feature a number of rule should be enforced :
    - the subclass should accept all the parameters from the base class
    - all creation arguments must be stored in creation_kwargs. Failing to do
    this will result in the impossibility to use set_feat.

    Parameters
    ----------
    getter : optional
        Object used to access the instrument property value through the use
        of the driver. If absent the Feature will be considered write only.
        This is typically a string. If the default get behaviour is overwritten
        True should be passed to mark the property as readable.
    setter : optional
        Object used to set the instrument property value through the use
        of the driver. If absent the Feature will be considered read-only.
        This is typically a string. If the default set behaviour is overwritten
        True should be passed to mark the property as settable.
    extract : unicode or Parser, optional
        String or stringparser.Parser to use to extract the interesting value
        from the instrument answer.
    retries : int, optional
        Whether or not a failed communication should result in a new attempt
        to communicate after re-opening the communication. The value is used to
        determine how many times to retry.
    checks : unicode or tuple(2)
        Booelan tests to execute before anything else when attempting to get or
        set a feature. Multiple assertion can be separated with ';'. The
        driver driver can be accessed under the name driver and in a setter
        the value under the name value, ie the following assertion is correct:
        driver.voltage > value
        If a single string is provided it is used to run checks before get and
        set, if a tuple of length 2 is provided the first element is used for
        the get operation, the second for the set operation, None can be used
        to indicate no check should be performed.
        The check methods built from this are bound to the get_check and
        set_check names.
    discard : tuple or dict
        Tuple of names of features whose cached value should be discarded after
        setting the Feature or dictionary specifying a list of feature whose
        cache should be discarded under the 'features' key and a list of limits
        to discard under the 'limits' key.

    Attributes
    ----------
    name : unicode
        Name of the Feature. This is set by the HasFeatures driver and
        should not be manipulated by user code.
    creation_kwargs : dict
        Dictionary in which all the creation args should be stored to allow
        subclass customisation. This should not be manipulated by user code.

    """
    def __init__(self, getter=None, setter=None, extract='', retries=0,
                 checks=None, discard=None):
        self._getter = getter
        self._setter = setter
        self._retries = retries
        self._customs = {}

        self.creation_kwargs = {'getter': getter, 'setter': setter,
                                'retries': retries, 'checks': checks,
                                'extract': extract, 'discard': discard}

        super(Feature,
              self).__init__(self._get if getter is not None else None,
                             self._set if setter is not None else None,
                             self._del)

        if isinstance(getter, AbstractGetSetFactory):
            self.get = MethodType(getter.build_getter(), self)
        if isinstance(setter, AbstractGetSetFactory):
            self.set = MethodType(setter.build_setter(), self)

        if checks:
            self._build_checkers(checks)
        if discard:
            if not isinstance(discard, dict):
                discard = {'features': discard}
            self._discard = discard
            self.modify_behavior('post_set', self.discard_cache,
                                 ('discard', 'append'), True)

        if extract:
            if isinstance(extract, Parser):
                self._parser = extract
            else:
                self._parser = Parser(extract)
            self.modify_behavior('post_get', self.extract,
                                 ('extract', 'prepend'), True)
        self.name = ''

    def pre_get(self, driver):
        """Hook to perform checks before querying a value from the instrument.

        If anything goes wrong this method should raise the corresponding
        error.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.

        """
        pass

    def get(self, driver):
        """Acces the parent driver to retrieve the state of the instrument.

        By default this method falls back to calling the parent
        default_get_feature method. This behaviour can be customized by
        creating a _get_(feat name) method on the driver class.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.

        Returns
        -------
        value :
            The value as returned by the query method. If any formatting is
            necessary it should be done in the post_get method.

        """
        return driver.default_get_feature(self, self._getter)

    def post_get(self, driver, value):
        """Hook to alter the value returned by the underlying driver.

        This can be used to convert the answer from the instrument to a more
        human friendly representation. By default this is a no-op. This
        behaviour can be customized by creating a _post_get_(feat name) method
        on the driver class.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.
        value :
            Value as returned by the underlying driver.

        Returns
        -------
        formatted_value :
            Formatted value.

        """
        return value

    def pre_set(self, driver, value):
        """Hook to format the value passed to the Feature before sending it
        to the instrument.

        This can be used to convert the passed value to something easier to
        pass to the instrument. By default this is a no-op. This behaviour can
        be customized by creating a _pre_set_(feat name) method on the driver
        class.

        Parameters
        ----------
        driver : HasFeature
            Object on which this Feature is defined.
        value :
            Value as passed by the user.

        Returns
        -------
        i_value :
            Value which should be passed to the set method.

        """
        return value

    def set(self, driver, value):
        """Access the driver to actually set the instrument state.

        By default this method falls back to calling the parent
        default_set_feature method. This behavior can be customized by
        creating a _set_(feat name) method on the driver class.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.
        value :
            Object to pass to the driver method to set the value.

        """
        return driver.default_set_feature(self, self._setter, value)

    def post_set(self, driver, value, i_value, response):
        """Hook to perform additional action after setting a value.

        This can be used to check the instrument operated correctly or perform
        some cleanup. By default this falls back on the driver
        default_check_operation method. This behaviour can be customized
        by creating a _post_set_(feat name) method on the driver class.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.
        value :
            Value as passed by the user.
        i_value :
            Value which was passed to the set method.
        response :
            Return value of the set method.

        Raises
        ------
        I3pyError :
            Raised if the driver detects an issue.

        """
        self.check_operation(driver, value, i_value, response)

    def check_operation(self, driver, value, i_value, response):
        """Check the instrument operated correctly.

        This uses the driver default_check_operation method.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.
        value :
            Value as passed by the user.
        i_value :
            Value which was passed to the set method.
        response :
            Return value of the set method.

        Raises
        ------
        I3pyError :
            Raised if the driver detects an issue.

        """
        res, details = driver.default_check_operation(self, value, i_value,
                                                      response)
        if not res:
            mess = 'The instrument did not succeed to set {} to {} ({})'
            if details:
                mess += ':' + str(details)
            else:
                mess += '.'
            raise I3pyError(mess.format(self.name, value, i_value))

    def discard_cache(self, driver, value, i_value, response):
        """Empty the cache of the specified values.

        """
        if 'features' in self._discard:
            driver.clear_cache(features=self._discard['features'])
        if 'limits' in self._discard:
            driver.discard_limits(self._discard['limits'])

    def extract(self, driver, value):
        """Extract the return value using the extract value.

        """
        return self._parser(value)

    def clone(self):
        """Clone the Feature by copying all the local attributes and driver
        methods

        """
        p = self.__class__(self._getter, self._setter, retries=self._retries)
        p.__doc__ = self.__doc__

        for k, v in self.__dict__.items():
            if isinstance(v, MethodType):
                setattr(p, k, MethodType(v.__func__, p))
            elif hasattr(v, 'clone'):
                setattr(p, k, v.clone())
            elif isinstance(v, dict):
                setattr(p, k, v.copy())
            else:
                setattr(p, k, v)

        return p

    def _build_checkers(self, checks):
        """Create the custom check function and bind them to check_get and
        check_set.

        """
        build = build_checker
        if len(checks) != 2:
            checks = (checks, checks)

        if checks[0]:
            self.get_check = MethodType(build(checks[0], '(self, driver)'),
                                        self)
        if checks[1]:
            self.set_check = MethodType(build(checks[1],
                                              '(self, driver, value)',
                                              'value'),
                                        self)

        if hasattr(self, 'get_check'):
            self.modify_behavior('pre_get', self.get_check,
                                 ('checks', 'prepend'), True)
        if hasattr(self, 'set_check'):
            self.modify_behavior('pre_set', self.set_check,
                                 ('checks', 'prepend'), True)

    def _get(self, driver):
        """Getter defined when the user provides a value for the get arg.

        """
        with driver.lock:
            cache = driver._cache
            name = self.name
            if name in cache:
                return cache[name]

            val = get_chain(self, driver)
            if driver.use_cache:
                cache[name] = val

            return val

    def _set(self, driver, value):
        """Setter defined when the user provides a value for the set arg.

        """
        with driver.lock:
            cache = driver._cache
            name = self.name
            if name in cache and value == cache[name]:
                return

            set_chain(self, driver, value)
            if driver.use_cache:
                cache[name] = value

    def _del(self, driver):
        """Deleter clearing the cache of the instrument for this Feature.

        """
        driver.clear_cache(features=(self.name,))


def get_chain(feat, driver):
    """Generic get chain for Features.

    """
    i = -1
    feat.pre_get(driver)

    while i < feat._retries:
        try:
            i += 1
            val = feat.get(driver)
            break
        except driver.retries_exceptions as e:
            if i != feat._retries or not driver.check_error(feat.name, e):
                driver.reopen_connection()
                continue
            else:
                raise

    alt_val = feat.post_get(driver, val)

    return alt_val


def set_chain(feat, driver, value):
    """Generic set chain for Features.

    """
    i_val = feat.pre_set(driver, value)
    i = -1
    while i < feat._retries:
        try:
            i += 1
            resp = feat.set(driver, i_val)
            break
        except driver.retries_exceptions:
            if i != feat._retries:
                driver.reopen_connection()
                continue
            else:
                raise
    feat.post_set(driver, value, i_val, resp)
