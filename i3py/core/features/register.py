# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module defining a Feature used to deal with 8-bits binary register.

"""
from enum import IntFlag
from typing import Any, Union, Optional, Dict, Tuple, Type

from .feature import Feature
from ..utils import create_register_flag
from ..abstracts import AbstractHasFeatures


class Register(Feature):
    """Property handling a bit field as an IntFlag.

    Parameters
    ----------
    names : tuple or dict
        Names to associate to each bit fields from 0 to length-1. When using an
        iterable None can be used to mark a useless bit. When using a dict
        the values are used to specify the bits to consider.

    length : int, optional
        Length of the bit field. Should be a multiple of 8. 8 is the default
        value.

    """
    #: Attribute in which the custom class to represent the Feature values is
    #: stored
    flag: Optional[Type[IntFlag]]

    def __init__(self, getter: Any=None,
                 setter: Any=None,
                 names: Union[Tuple[Optional[str], ...], Dict[str, int]]=(),
                 length: int=8,
                 extract: str='',
                 retries: int=0,
                 checks: Optional[str]=None,
                 discard: Optional[Union[Tuple[str, ...],
                                         Dict[str, Tuple[str, ...]]]]=None,
                 options: Optional[str]=None) -> None:
        Feature.__init__(self, getter, setter, extract, retries,
                         checks, discard, options)

        self.creation_kwargs['names'] = names
        self.creation_kwargs['length'] = length
        self.flag = None

        self.modify_behavior('post_get', self.int_to_flag.__func__,
                             ('prepend',), 'int_to_flag', True)

        self.modify_behavior('pre_set', self.flag_to_int.__func__,
                             ('append',), 'flag_to_int', True)

    def int_to_flag(self, driver: AbstractHasFeatures, value: int) -> IntFlag:
        """Convert the byte returned by the instrument to a dict.

        """
        val = int(value)
        return self.flag(val)

    def flag_to_int(self, driver: AbstractHasFeatures, value: IntFlag) -> int:
        """Convert a flag into a byte value.

        """
        return int(value)

    def __set_name__(self, owner: type, name: str):
        """Use set name to construct the flag class once we get our name.

        """
        self.flag = create_register_flag(name.capitalize() + 'Flag',
                                         self.creation_kwargs['names'],
                                         self.creation_kwargs['length'])
