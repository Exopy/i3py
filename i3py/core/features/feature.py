# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base descriptor for all instrument properties declaration.

"""
from types import MethodType
from typing import Any, Union, Optional, Dict, Tuple, Callable, cast
from time import perf_counter, sleep

from stringparser import Parser
from inspect import signature

from ..errors import I3pyError, I3pyFailedGet, I3pyFailedSet
from ..utils import build_checker, check_options
from ..abstracts import (AbstractFeature, AbstractGetSetFactory,
                         AbstractHasFeatures)
from ..composition import (SupportMethodCustomization, normalize_signature)


class Feature(SupportMethodCustomization, property):
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
    extract : str or Parser, optional
        String or stringparser.Parser to use to extract the interesting value
        from the instrument answer.
    retries : int, optional
        Whether or not a failed communication should result in a new attempt
        to communicate after re-opening the communication. The value is used to
        determine how many times to retry.
    checks : str or tuple(2)
        Booelan tests to execute before anything else when attempting to get or
        set a feature. Multiple assertion can be separated with ';'. The
        driver can be accessed under the name driver and in a setter the value
        under the name value, ie the following assertion is correct:
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
    options: str
        Assertions in the form option_name['option_field'] == possible_values
        or any other valid boolean test. Multiple assertions can be separated
        by ; . Always apply to both get and set. The result of this
        computation is cached for reduced cost.

    Attributes
    ----------
    name : str
        Name of the Feature. This is set by the HasFeatures driver and
        should not be manipulated by user code.
    creation_kwargs : dict
        Dictionary in which all the creation args should be stored to allow
        subclass customisation. This should not be manipulated by user code.

    """

    def __init__(self, getter: Any=None,
                 setter: Any=None,
                 extract: str='',
                 retries: int=0,
                 checks: Optional[str]=None,
                 discard: Optional[Union[Tuple[str, ...],
                                         Dict[str, Tuple[str, ...]]]]=None,
                 options: Optional[str]=None) -> None:
        self._getter = getter
        self._setter = setter
        self._retries = retries
        self._customs = {}
        self.__doc__ = ''
        self.name = ''

        self.creation_kwargs = {'getter': getter, 'setter': setter,
                                'retries': retries, 'checks': checks,
                                'extract': extract, 'discard': discard,
                                'options': options}

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
            self.modify_behavior('post_set', self.discard_cache.__func__,
                                 ('append',), 'discard', internal=True)

        if extract:
            if isinstance(extract, Parser):
                self._parser = extract
            else:
                self._parser = Parser(extract)
            self.modify_behavior('post_get', self.extract.__func__,
                                 ('prepend',), 'extract', internal=True)

        self._use_options = bool(options)

    def make_doc(self, doc: str):
        """Build the doc of the feature based on the passed string and kwargs.

        """
        ftype = ('read/write ' if (self.creation_kwargs['getter'] and
                                   self.creation_kwargs['setter'])
                 else ('read only' if self.creation_kwargs['getter'] else
                       'write only'))
        doc += '\nThis %s feature is %s.' % (type(self).__name__, ftype)
        if self.creation_kwargs['options']:
            options = self.creation_kwargs['options']
            doc += ('\nThe following options must be set for the feature to be'
                    'usable:\n  - %s' % options)
        if self.creation_kwargs['checks']:
            checks = self.creation_kwargs['checks']
            if isinstance(checks, tuple):
                doc += ('\nThe following checks are run :\n  - on get: %s\n'
                        '  - on set: %s') % (checks[0], checks[1])
            else:
                doc += ('\nThe following checks are run on get and '
                        'set:\n  - %s' % checks)
        if self.creation_kwargs['discard']:
            discard = self.creation_kwargs['discard']
            if isinstance(discard, dict):
                doc += ('\nOn set operation the following cached values are '
                        'cleared:\n' +
                        '\n'.join(' - %s: %s' % (k, ', '.join(v))
                                  for k, v in discard.items()))
            else:
                doc += ('On set operation the following cached values are '
                        'cleared:\n -  features: %s') % ', '.join(discard)

        self.__doc__ = doc

    def pre_get(self, driver: AbstractHasFeatures):
        """Hook to perform checks before querying a value from the instrument.

        If anything goes wrong this method should raise the corresponding
        error.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.

        """
        pass

    def get(self, driver: AbstractHasFeatures) -> Any:  # type: ignore
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

    def post_get(self, driver: AbstractHasFeatures, value: Any) -> Any:
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

    def pre_set(self, driver: AbstractHasFeatures, value: Any) -> Any:
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

    def set(self,  # type: ignore
            driver: AbstractHasFeatures,
            value: Any) -> Any:
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

        Returns
        -------
        response : object
            Response from the driver.

        """
        return driver.default_set_feature(self, self._setter, value)

    def post_set(self, driver: AbstractHasFeatures, value: Any, i_value: Any,
                 response: Any):
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

    def check_operation(self, driver: AbstractHasFeatures, value: Any,
                        i_value: Any, response: Any):
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

    def discard_cache(self, driver: AbstractHasFeatures, value: Any,
                      i_value: Any, response: Any):
        """Empty the cache of the specified values.

        Used as a post-set modifier.

        """
        if 'features' in self._discard:
            driver.clear_cache(features=self._discard['features'])
        if 'limits' in self._discard:
            driver.discard_limits(self._discard['limits'])

    def extract(self, driver: AbstractHasFeatures, value: str) -> Any:
        """Extract the return value using the extract value.

        """
        return self._parser(value)

    def check_options(self, driver: AbstractHasFeatures):
        """Check that the driver options allow to use this feature.

        """
        op, msg = driver._settings[self.name]['_options']
        if op:
            return
        elif op is None:
            op, msg = check_options(driver, self.creation_kwargs['options'])
            driver._settings[self.name]['_options'] = op, msg
            if op:
                return

        msg = 'Options does not allow to access %s : %s' % (self.name, msg)
        raise AttributeError(msg)

    def clone(self) -> AbstractFeature:
        """Clone the Feature by copying all the local attributes and driver
        methods

        """
        new = type(self)(**self.creation_kwargs)
        new.copy_custom_behaviors(self)
        new.name = self.name
        new.__doc__ = self.__doc__

        return new

    def create_default_settings(self) -> Dict[str, Any]:
        """Create the default settings for a feature.

        """
        settings: Dict[str, Any] = {'inter_set_delay': 0, '_last_set': 0}
        if self._use_options:
            settings['_options'] = (None, '')
        return settings

    @property
    def self_alias(self) -> str:
        """For features self is replaced by feat in function signature.

        """
        return 'feat'

    def analyse_function(self, method_name: str, func: Callable,
                         specifiers: Tuple[str, ...]):
        """Check the signature of the function.

        """
        sig, chain = {'pre_get': (('feat', 'driver'), None),
                      'get': (('feat', 'driver'), None),
                      'post_get': (('feat', 'driver', 'value'), 'value'),
                      'pre_set': (('feat', 'driver', 'value'), 'value'),
                      'set': (('feat', 'driver', 'value'), None),
                      'post_set': (('feat', 'driver', 'value', 'i_value',
                                    'response'),
                                   None)
                      }[method_name]
        if method_name in ('get', 'set') and specifiers:
            msg = ('Can only replace {} method of a feature, not customize it.'
                   ' Failed on Feature {} with customization specifications {}'
                   )
            raise ValueError(msg.format(method_name, self.name, specifiers))

        if method_name in ('pre_get', 'post_get', 'pre_set'):
            unbound = getattr(Feature, method_name)
            original = getattr(unbound, '__func__', unbound)
            if getattr(self, method_name).__func__ is original:
                specifiers = ()

        func_sig = normalize_signature(signature(func), self.self_alias)
        if sig != func_sig:
            msg = ('Function {} used to attempt to customize method {} of '
                   'feature {} does not have the right signature (expected={},'
                   ' provided={}).')
            raise ValueError(msg.format(func.__name__, method_name, self.name,
                                        sig, func_sig))

        return specifiers, [sig], chain

    def _build_checkers(self, checks: Union[str, Tuple[str, str]]) -> None:
        """Create the custom check function and bind them to check_get and
        check_set.

        """
        build = build_checker
        if len(checks) != 2:
            checks = cast(str, checks)
            checks = (checks, checks)

        if checks[0]:
            self.get_check = build(checks[0], '(feat, driver)')
        if checks[1]:
            self.set_check = build(checks[1], '(feat, driver, value)', 'value')

        if hasattr(self, 'get_check'):
            self.modify_behavior('pre_get', self.get_check,
                                 ('prepend',), 'checks', internal=True)
        if hasattr(self, 'set_check'):
            self.modify_behavior('pre_set', self.set_check,
                                 ('prepend',), 'checks', internal=True)

    def _get(self, driver: AbstractHasFeatures) -> Any:
        """Getter defined when the user provides a value for the get arg.

        """
        if self._use_options:
            self.check_options(driver)
        try:
            with driver.lock:
                cache = driver._cache
                name = self.name
                if name in cache:
                    return self._read_cache(driver, cache, name)

                val = get_chain(self, driver)
                if driver._use_cache:
                    self._fill_cache(driver, cache, name, val)

                return val
        except I3pyFailedGet:
            raise
        except Exception as e:
            msg = 'Failed to get the value of feature {} for driver {}.'
            raise I3pyFailedGet(msg.format(self.name, driver)) from e

    def _set(self, driver: AbstractHasFeatures, value: Any):
        """Setter defined when the user provides a value for the set arg.

        """
        if self._use_options:
            self.check_options(driver)

        settings = driver._settings[self.name]
        isd = settings['inter_set_delay']
        if isd:
            elapsed = perf_counter() - settings['_last_set']
            if elapsed < isd:
                sleep(isd - elapsed)
        try:
            with driver.lock:
                cache = driver._cache
                name = self.name
                if self._is_value_cached(driver, cache, name, value):
                    return

                set_chain(self, driver, value)
                if driver._use_cache:
                    self._fill_cache(driver, cache, name, value)
        except I3pyFailedSet:
            raise  # pragma: no cover
        except Exception as e:
            msg = 'Failed to set the value of feature {} to {} for driver {}.'
            raise I3pyFailedSet(msg.format(self.name, value, driver)) from e
        finally:
            if isd:
                settings['_last_set'] = perf_counter()

    def _del(self, driver: AbstractHasFeatures):
        """Deleter clearing the cache of the instrument for this Feature.

        """
        driver.clear_cache(features=(self.name,))

    def _read_cache(self, driver: AbstractHasFeatures,
                    cache: Dict[str, Any], name: str) -> Any:
        """Return the value stored in the cache.

        """
        return cache[name]

    def _is_value_cached(self, driver: AbstractHasFeatures,
                         cache: Dict[str, Any], name: str, value: Any) -> bool:
        """Check if a value is cached, which means set is supefluous.

        """
        return name in cache and value == cache[name]

    def _fill_cache(self, driver: AbstractHasFeatures, cache: Dict[str, Any],
                    name: str, value: Any):
        """Fill the cache value.

        """
        cache[name] = value


AbstractFeature.register(Feature)


def get_chain(feat: Feature, driver: AbstractHasFeatures) -> Any:
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
            if i != feat._retries:
                driver.reopen_connection()
                continue
            else:
                raise

    alt_val = feat.post_get(driver, val)

    return alt_val


def set_chain(feat: Feature, driver: AbstractHasFeatures, value: Any):
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
