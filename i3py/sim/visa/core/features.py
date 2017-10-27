# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Feature like object describing an instrument feature.

"""
import re
from collections import OrderedDict

from stringparser import Parser
from i3py.core.features import AbstractFeature

from .common import build_matcher
from .component import ErrorOccured, NoResponse


# XXX setter should containe a value field
class SimulatedFeature(AbstractFeature):
    """Feature describing a simulated instrument feature.

    Parameters
    ----------

    """
    def __init__(self, getter=None, setter=None, default=None,
                 answer_formats=None, checks=None, discard=None, types=(),
                 limits=None, values=None, errors=None):
        super(SimulatedFeature, self).__init__()
        if getter:
            if '{' in getter:
                self._getter_matcher = re.compile('^' + build_matcher(getter))
                self._getter_extract = Parser(getter)
            else:
                self._getter_matcher = re.compile('^' + getter)
                self._getter_extract = None
        else:
            self._getter_matcher = None

        if setter:
            if '{value' not in setter:
                raise ValueError('Setting queries should have a {value} field')
            self._setter_matcher = re.compile('^' + build_matcher(setter))
            self._setter_extract = Parser(setter)
        else:
            self._setter_matcher = None

        # XXX set the creation_kwargs
        self.creation_kwargs = {}

        # XXX handle all magic arguments

    def link_to_component(self, component, root):
        """
        """
        pass

    def match(self, driver, query):
        """Try to match the query to the getter and setter.

        """
        if self._getter_matcher is not None:
            if self._getter_matcher.match(query):
                if self._getter_extract:
                    try:
                        kwargs = self._getter_extract(query)
                    except ValueError as e:
                        driver.handle_error(e)
                        return ErrorOccured
                else:
                    kwargs = {}
                return self.format_answer(driver, 'get',
                                          getattr(driver, self.name), **kwargs)

        if self._setter_matcher is not None:
            if self._setter_matcher.match(query):
                if self._setter_extract:
                    try:
                        kwargs = self._setter_extract(query)
                    except ValueError as e:
                        driver.handle_error(e)
                        return ErrorOccured
                else:
                    kwargs = {}
                value = kwargs['value']
                setattr(driver, self.name, value)
                return self.format_answer(driver, 'set', value, **kwargs)

        return NoResponse

    def format_answer(self, driver, kind, value, **kwargs):
        """Format the answer to a command.

        """
        if kind in self._answer_formats:
            return self._answer_formats[kind].format(value, **kwargs)

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

        By default this method falls back to reading the cached value or the
        provided default.

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
        return driver._cache.get(self.name, self.get_default(driver))

    def post_get(self, driver, value):
        """Hook to alter the value returned by the underlying driver.

        By default this is a no-op.

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

    def _get(self, driver):
        """Getter function used if the getter passed is not None.

        """
        self.pre_get(driver)
        val = self.get(driver)
        return self.post_get(driver, val)

    def pre_set(self, driver, value):
        """Hook to format the value passed to the Feature before caching it.

        By default this is a no-op.

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
        """Set the value in the cache.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.
        value :
            Object to pass to the driver method to set the value.

        """
        driver._cache[self.name] = value
        return None

    def post_set(self, driver, value, i_value, response):
        """Hook to perform additional action after setting a value.

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

    def _set(self, driver, value):
        """Setter function used if the setter passed is not None.

        """
        i_value = self.pre_set(driver, value)
        resp = self.set(driver, i_value)
        return self.post_set(driver, value, i_value, resp)

    def get_default(self, driver):
        """Query the default value for the feature if the cache is not set.

        By default this simply return the value provided to the constructor.

        """
        return self._default


class SimulatedRegister(SimulatedFeature):
    """
    """
    def match(self, query):
        """
        """
        pass


class ErrorQueue(AbstractFeature):
    """
    """
    def match(self, query):
        """
        """
        pass


class StatusRegister(object):

    def __init__(self, values):
        object.__init__(self)
        self._value = 0
        self._error_map = {}
        for name, value in values.items():
            if name == 'q':
                continue
            self._error_map[name] = int(value)

    def set(self, error_key):
        self._value = self._value | self._error_map[error_key]

    def keys(self):
        return self._error_map.keys()

    @property
    def value(self):
        return to_bytes(str(self._value))

    def clear(self):
        self._value = 0


class ErrorQueue(object):

    def __init__(self, values):

        super(ErrorQueue, self).__init__()
        self._queue = []
        self._error_map = {}
        for name, value in values.items():
            if name in ('q', 'default', 'strict'):
                continue
            self._error_map[name] = to_bytes(value)
        self._default = to_bytes(values['default'])

    def append(self, err):
        if err in self._error_map:
            self._queue.append(self._error_map[err])

    @property
    def value(self):
        if self._queue:
            return self._queue.pop(0)
        else:
            return self._default

    def clear(self):
        self._queue = []
