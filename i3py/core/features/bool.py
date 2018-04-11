# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Feature for boolean like values.

"""
from typing import Any, Dict, Optional, Sequence, Tuple, Union

from ..abstracts import AbstractHasFeatures
from .mapping import Mapping


class Bool(Mapping):
    """ Boolean property.

    True/False are mapped to the mapping values, aliases can also be declared
    to accept non-boolean values.

    Parameters
    ----------
    aliases : dict, optional
        Keys should be True and False and values the list of aliases.

    """
    def __init__(self,
                 getter: Any=None,
                 setter: Any=None,
                 mapping: Optional[dict]=None,
                 aliases: Optional[Dict[bool, Sequence]]=None,
                 extract: str='',
                 retries: int=0,
                 checks: Optional[str]=None,
                 discard: Optional[Union[Tuple[str, ...],
                                         Dict[str, Tuple[str, ...]]]]=None,
                 options: Optional[str]=None) -> None:
        Mapping.__init__(self, getter, setter, mapping, extract,
                         retries, checks, discard, options)

        self._aliases = {True: True, False: False}
        if aliases:
            for k in aliases:
                for v in aliases[k]:
                    self._aliases[v] = k
        self.creation_kwargs['aliases'] = aliases

    def map_value(self, driver: AbstractHasFeatures, value: Any):
        self._aliases[value]
        return self._map[self._aliases[value]]
