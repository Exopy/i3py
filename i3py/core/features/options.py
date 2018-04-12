# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Feature for instrument options.

"""
from typing import Any, Union, Optional, Dict, Tuple

from .feature import Feature
from ..abstracts import AbstractOptions


class Options(Feature):
    """Feature used to access the options of an instrument.

    Options in I3py are considered static (ie related to the hardware or
    firmware) and are hence read only. Because there is no generic pattern
    in the formatting of the options, the user is expected to implement
    manually the getter function.

    """
    def __init__(self, getter: bool=True,
                 setter: Any=None,
                 extract: str='',
                 retries: int=0,
                 checks: Optional[str]=None,
                 discard: Optional[Union[Tuple[str, ...],
                                         Dict[str, Tuple[str, ...]]]]=None,
                 options: Optional[str]=None) -> None:

        if setter is not None:
            raise ValueError('Options is read-only can have a setter.')
        Feature.__init__(self, getter, None, extract, retries,
                         checks, discard, options)


AbstractOptions.register(Options)
