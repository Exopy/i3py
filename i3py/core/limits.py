# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module defining the limits utilities used for int and float.

"""
from functools import update_wrapper
from math import modf
from types import MethodType
from typing import Callable, Optional, Union

from .abstracts import AbstractLimitsValidator
from .unit import UNIT_SUPPORT, get_unit_registry

if UNIT_SUPPORT:
    from pint.quantity import _Quantity


class IntLimitsValidator(AbstractLimitsValidator):
    """Limits used to validate a the value of an integer.

    Parameters
    ----------
    min : int, optional
        Minimal allowed value
    max : int, optional
        Maximum allowed value
    step : int, optional
        Smallest allowed step

    Methods
    -------
    validate :
        Validate a given value. If a unit is declared both floats and Quantity
        can be passed.

    """

    __slots__ = ()

    def __init__(self, min: Optional[int]=None, max: Optional[int]=None,
                 step: Optional[int]=None) -> None:
        mess = 'The {} of an IntRange must be an integer not {}.'
        if min is None and max is None:
            raise ValueError('An IntLimitsValidator must have a min or max')
        if min is not None and not isinstance(min, int):
            raise TypeError(mess.format('min', type(min)))
        if max is not None and not isinstance(max, int):
            raise TypeError(mess.format('max', type(max)))
        if step and not isinstance(step, int):
            raise TypeError(mess.format('step', type(step)))

        self.minimum = min
        self.maximum = max
        self.step = step

        if min is not None:
            if max is not None:
                if step:
                    self.validate = self._validate_range_and_step
                else:
                    self.validate = self._validate_range
            else:
                if step:
                    self.validate = self._validate_larger_and_step
                else:
                    self.validate = self._validate_larger
        else:
            if step:
                self.validate = self._validate_smaller_and_step
            else:
                self.validate = self._validate_smaller

    def _validate_smaller(self, value: int) -> bool:
        """Check if the value is smaller than the maximum.

        """
        return value <= self.maximum

    def _validate_smaller_and_step(self, value: int) -> bool:
        """Check if the value is smaller than the maximum and respect the step.

        """
        return value <= self.maximum and (value-self.maximum) % self.step == 0

    def _validate_larger(self, value: int) -> bool:
        """Check if the value is larger than the minimum.

        """
        return value >= self.minimum

    def _validate_larger_and_step(self, value: int) -> bool:
        """Check if the value is larger than the minimum and respect the step.

        """
        return value >= self.minimum and (value-self.minimum) % self.step == 0

    def _validate_range(self, value: int) -> bool:
        """Check if the value is in the range.

        """
        return self.minimum <= value <= self.maximum

    def _validate_range_and_step(self, value: int) -> bool:
        """Check if the value is in the range and respect the step.

        """
        return self.minimum <= value <= self.maximum\
            and (value-self.minimum) % self.step == 0


class FloatLimitsValidator(AbstractLimitsValidator):
    """Range used to validate a the value of an integer.

    Parameters
    ----------
    min : float, optional
        Minimal allowed value
    max : float, optional
        Maximum allowed value
    step : float, optional
        Smallest allowed step
    unit : str, optional
        Unit in which the bounds and step are expressed.

    Attributes
    ----------
    unit : Unit or None
        Unit used when validating.

    Methods
    -------
    validate :
        Validate a given value. If a unit is declared both floats and Quantity
        can be passed. When passing a float the unit can be given as a keyword.
        This is used when validating Float features.

    """

    __slots__ = ('unit')

    def __init__(self, min: Optional[float]=None, max: Optional[float]=None,
                 step: Optional[float]=None, unit: str=None) -> None:
        mess = 'The {} of an FloatLimitsValidator must be a float not {}.'
        if min is None and max is None:
            raise ValueError('An FloatLimitsValidator must have a min or max')
        if min is not None and not isinstance(min, (int, float)):
            raise TypeError(mess.format('min', type(min)))
        if max is not None and not isinstance(max, (int, float)):
            raise TypeError(mess.format('max', type(max)))
        if step and not isinstance(step, (int, float)):
            raise TypeError(mess.format('step', type(step)))

        self.minimum = float(min) if min is not None else None
        self.maximum = float(max) if max is not None else None
        self.step = float(step) if step is not None else None

        if UNIT_SUPPORT and unit:
            ureg = get_unit_registry()
            self.unit = ureg.parse_expression(unit)
            wrap = self._unit_conversion
        else:
            wrap = lambda x: x  # type: ignore

        if min is not None:
            if max is not None:
                if step:
                    self.validate = wrap(self._validate_range_and_step)
                else:
                    self.validate = wrap(self._validate_range)
            else:
                if step:
                    self.validate = wrap(self._validate_larger_and_step)
                else:
                    self.validate = wrap(self._validate_larger)
        else:
            if step:
                self.validate = wrap(self._validate_smaller_and_step)
            else:
                self.validate = wrap(self._validate_smaller)

    def _unit_conversion(self,
                         cmp_func: Union[MethodType,
                                         Callable[['FloatLimitsValidator',
                                                   float, Optional[str]],
                                                  bool]]
                         ) -> (MethodType):
        """Decorator handling unit conversion to the unit.

        """
        if isinstance(cmp_func, MethodType):
            cmp_func = cmp_func.__func__

        def wrapper(self, value, unit=None):
            if unit and unit != self.unit:
                value *= (1*unit).to(self.unit).magnitude

            elif isinstance(value, _Quantity):
                value = value.to(self.unit).magnitude

            return cmp_func(self, value)

        update_wrapper(wrapper, cmp_func)
        wrapper.__doc__ += '\nAutomatic handling of unit conversions'
        return MethodType(wrapper, self)

    def _validate_smaller(self, value: float, unit: Optional[str]=None
                          ) -> bool:
        """Check if the value is smaller than the maximum.

        """
        return value <= self.maximum

    def _validate_smaller_and_step(self, value: float, unit: Optional[str]=None
                                   ) -> bool:
        """Check if the value is smaller than the maximum and respect the step.

        """
        ratio = round(abs((value-self.maximum)/self.step), 9)
        return value <= self.maximum and modf(ratio)[0] < 1e-9

    def _validate_larger(self, value: float, unit: Optional[str]=None
                         ) -> bool:
        """Check if the value is larger than the minimum.

        """
        return value >= self.minimum

    def _validate_larger_and_step(self, value: float, unit: Optional[str]=None
                                  ) -> bool:
        """Check if the value is larger than the minimum and respect the step.

        """
        ratio = round(abs((value-self.minimum)/self.step), 9)
        return value >= self.minimum and modf(ratio)[0] < 1e-9

    def _validate_range(self, value: float, unit: Optional[str]=None
                        ) -> bool:
        """Check if the value is in the range.

        """
        return self.minimum <= value <= self.maximum

    def _validate_range_and_step(self, value: float, unit: Optional[str]=None
                                 ) -> bool:
        """Check if the value is in the range and respect the step.

        """
        ratio = round(abs((value-self.minimum)/self.step), 9)
        return self.minimum <= value <= self.maximum\
            and abs(modf(ratio)[0]) < 1e-9
