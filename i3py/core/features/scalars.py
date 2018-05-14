# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Features for scalars values such float, int, string, etc...

"""
from typing import Any, Dict, Optional, Tuple, Union

from ..abstracts import AbstractHasFeatures, AbstractLimitsValidator
from ..limits import FloatLimitsValidator, IntLimitsValidator
from ..unit import FLOAT_QUANTITY, UNIT_RETURN, UNIT_SUPPORT, get_unit_registry
from ..utils import raise_limits_error
from .enumerable import Enumerable
from .limits_validated import LimitsValidated
from .mapping import Mapping

if UNIT_SUPPORT:
    from pint.quantity import _Quantity


class Str(Mapping, Enumerable):
    """ Feature casting the instrument answer to a str, support enumeration.

    """
    def __init__(self, getter: Any=None,
                 setter: Any=None,
                 values: Tuple[str, ...]=(),
                 mapping: Optional[dict]=None,
                 extract: str='',
                 retries: int=0,
                 checks: Union[Optional[str],
                               Tuple[Optional[str], Optional[str]]]=None,
                 discard: Optional[Union[Tuple[str, ...],
                                         Dict[str, Tuple[str, ...]]]]=None,
                 options: Optional[str]=None) -> None:

        if mapping:
            Mapping.__init__(self, getter, setter, mapping, extract,
                             retries, checks, discard)
        else:
            Enumerable.__init__(self, getter, setter, values, extract,
                                retries, checks, discard)

        self.modify_behavior('post_get', self.cast_to_str.__func__,
                             ('append',), 'cast_to_str', True)

    def cast_to_str(self, driver: AbstractHasFeatures, value: Any) -> str:
        return str(value)


class Int(LimitsValidated, Mapping, Enumerable):
    """ Property casting the instrument answer to an int.

    Support enumeration or range validation (the range takes precedence).

    """
    def __init__(self, getter: Any=None,
                 setter: Any=None,
                 values: Tuple[int, ...]=(),
                 mapping: Optional[dict]=None,
                 limits: Optional[Union[str, AbstractLimitsValidator,
                                        Tuple]]=None,
                 extract: str='',
                 retries: int=0,
                 checks: Union[Optional[str],
                               Tuple[Optional[str], Optional[str]]]=None,
                 discard: Optional[Union[Tuple[str, ...],
                                         Dict[str, Tuple[str, ...]]]]=None,
                 options: Optional[str]=None) -> None:
        if mapping:
            Mapping.__init__(self, getter, setter, mapping, extract,
                             retries, checks, discard)
        elif values and not limits:
            Enumerable.__init__(self, getter, setter, values, extract,
                                retries, checks, discard)
        else:
            if isinstance(limits, (tuple, list)):
                limits = IntLimitsValidator(*limits)
            LimitsValidated.__init__(self, getter, setter, limits, extract,
                                     retries, checks, discard)

        self.modify_behavior('post_get', self.cast_to_int.__func__,
                             ('append',), 'cast', True)

    def cast_to_int(self, driver: AbstractHasFeatures, value: Any) -> int:
        """Cast the value returned by the instrument to an int.

        """
        return int(value)


class Float(LimitsValidated, Mapping, Enumerable):
    """ Property casting the instrument answer to a float or Quantity.

    Support range validation and unit conversion.

    This Feature handle the cache in a specific fashion as values can have a
    unit but may be specified without one.

    """
    def __init__(self, getter: Any=None,
                 setter: Any=None,
                 values: Tuple[float, ...]=(),
                 mapping: Optional[dict]=None,
                 limits: Optional[Union[str, AbstractLimitsValidator,
                                        Tuple]]=None,
                 unit: Optional[str]=None,
                 extract: str='',
                 retries: int=0,
                 checks: Union[Optional[str],
                               Tuple[Optional[str], Optional[str]]]=None,
                 discard: Optional[Union[Tuple[str, ...],
                                         Dict[str, Tuple[str, ...]]]]=None,
                 options: Optional[str]=None) -> None:
        if mapping:
            Mapping.__init__(self, getter, setter, mapping, extract,
                             retries, checks, discard, options)
        elif values and not limits:
            Enumerable.__init__(self, getter, setter, values, extract,
                                retries, checks, discard, options)
        else:
            if isinstance(limits, (tuple, list)):
                limits = FloatLimitsValidator(*limits, unit=unit)
            LimitsValidated.__init__(self, getter, setter, limits, extract,
                                     retries, checks, discard, options)

        if UNIT_SUPPORT and unit:
            ureg = get_unit_registry()
            self.unit = ureg.parse_expression(unit)
        else:
            self.unit = None

        self.creation_kwargs.update({'unit': unit, 'values': values,
                                     'limits': limits})

        if UNIT_SUPPORT:
            spec = (('add_before', 'validate') if (values or limits)
                    else ('prepend',))
            self.modify_behavior('pre_set',  self.convert.__func__,
                                 spec, 'convert',  True)

        self.modify_behavior('post_get', self.cast_to_float.__func__,
                             ('append',), 'cast', True)

    def create_default_settings(self) -> Dict[str, Any]:
        """Create the default settings for a feature.

        """
        settings = super().create_default_settings()
        settings['unit_return'] = UNIT_RETURN
        return settings

    def cast_to_float(self, driver: AbstractHasFeatures, value: Any
                      ) -> FLOAT_QUANTITY:
        """Cast the value returned by the instrument to float or Quantity.

        """
        fval = float(value)
        if (self.unit is not None and
                driver._settings[self.name]['unit_return']):
            return fval*self.unit

        else:
            return fval

    def convert(self, driver: AbstractHasFeatures, value: FLOAT_QUANTITY
                ) -> float:
        """Convert unit.

        """
        if isinstance(value, _Quantity):
            if self.unit:
                value = value.to(self.unit).magnitude
            else:
                raise ValueError('Cannot convert Quantity object when no unit '
                                 'is specified for the feature.')

        return value

    def validate_limits(self, driver: AbstractHasFeatures,
                        value: FLOAT_QUANTITY):
        """Make sure a value is in the given range.

        This method is meant to be used as a pre-set.

        """
        if not self.limits.validate(value, self.unit):
            raise_limits_error(self.name, value, self.limits)
        else:
            return value

    def _read_cache(self, driver: AbstractHasFeatures, cache: Dict[str, Any],
                    name: str) -> FLOAT_QUANTITY:
        """Read the cache and return a value in agreement with the settings.

        """
        if (UNIT_SUPPORT and self.unit is not None and
                not driver._settings[name]['unit_return']):
            return cache[name][0]
        else:
            return cache[name][-1]

    def _is_value_cached(self, driver: AbstractHasFeatures,
                         cache: Dict[str, Any], name: str,
                         value: FLOAT_QUANTITY) -> bool:
        """Check if the proposed value is among the cached values.

        """
        return name in cache and value in cache[name]

    def _fill_cache(self, driver: AbstractHasFeatures, cache: Dict[str, Any],
                    name: str, value: FLOAT_QUANTITY):
        """Set both magnitude and quantity in cache.

        """
        if UNIT_SUPPORT and self.unit is not None:
            if isinstance(value, _Quantity):
                value = (value.magnitude, value)
            else:
                value = (value, value*self.unit)
        else:
            value = (value,)
        cache[name] = value
