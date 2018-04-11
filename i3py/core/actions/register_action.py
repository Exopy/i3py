# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Convenience action use to warp a method reading a binary register.

"""
from enum import IntFlag
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

from ..abstracts import AbstractHasFeatures
from ..utils import create_register_flag
from .action import BaseAction


class RegisterAction(BaseAction):
    """Automatically convert the returned register value.

    The register should be returned as a integer and will be converted to a
    IntFlag subclass according to the provided mapping.

    All parameters must be passed as keyword arguments.

    Parameters
    ----------
    names : iterable or dict
        Names to associate to each bit fields from 0 to 7. When using an
        iterable None can be used to mark a useless bit. When using a dict
        the values are used to specify the bits to consider.

    length : int, optional
        Length of the bit field. Should be a multiple of 8. 8 is the default
        value.

    options : str, optional
        Assertions in the form option_name['option_field'] == possible_values
        or any other valid boolean test. Multiple assertions can be separated
        by ;

    checks : str, optional
        Booelan tests to execute before calling the function. Multiple
        assertions can be separated with ';'. All the method arguments are
        available in the assertion execution namespace so one can access to the
        driver using self and to the arguments using their name (the signature
        of the wrapper is made to match the signature of the wrapped method).

    Returns
    -------
    register : dict
        Dictionary mapping the field of the bit field to their value.

    """
    def __init__(self,
                 names: Union[Tuple[Optional[str], ...], Dict[str, int]],
                 length: int=8, **kwargs
                 ) -> None:
        kwargs['names'] = names
        kwargs['length'] = length
        super().__init__(**kwargs)
        self.flag: Type[IntFlag] = None

    def customize_call(self, func: Callable, kwargs: Dict[str, Any]):
        """Store the function in call attributes and customize pre/post based
        on the kwargs.

        """
        super().customize_call(func, kwargs)
        self.add_register_conversion()

    def add_register_conversion(self):
        """Wrap a func using Pint to automatically convert Quantity to float.

        """
        def convert_byte(action, driver, result, *args, **kwargs):
            """Convert the result to a dictionary describing the register.

            """
            return action.flag(result)

        self.modify_behavior('post_call', convert_byte, ('prepend',),
                             'names', internal=True)

    def __set_name__(self, owner: AbstractHasFeatures, name: str):
        """Use set name to construct the flag class once we get our name.

        """
        self.flag = create_register_flag(name.capitalize() + 'Flag',
                                         self.creation_kwargs['names'],
                                         self.creation_kwargs['length'])
