# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Feature for values requiring a mapping between user and instrs values.

"""
from typing import Any, Dict, Optional, Sequence, Tuple, Union, cast

from ..abstracts import AbstractHasFeatures
from .feature import Feature


class Mapping(Feature):
    """ Feature using a dict to map user input to instrument and back.

    Parameters
    ----------
    mapping : dict or tuple
        Mapping between the user values and instrument values. If a tuple is
        provided the first element should be the mapping between user values
        and instrument input, the second between instrument output and user
        values. This allows to handle asymmetric case in which the instrument
        expect a command (ex: CMD ON) but when queried return 1. None can be
        used to mark that the mapping should only occur in one direction.

    """

    def __init__(self, getter: Any=None,
                 setter: Any=None,
                 mapping: Optional[Union[Sequence[dict], dict]]=None,
                 extract: str='',
                 retries: int=0,
                 checks: Optional[str]=None,
                 discard: Optional[Union[Tuple[str, ...],
                                         Dict[str, Tuple[str, ...]]]]=None,
                 options: Optional[str]=None) -> None:
        Feature.__init__(self, getter, setter, extract, retries,
                         checks, discard, options)

        mapping = mapping or {}

        if isinstance(mapping, (tuple, list)):
            self._map = mapping[0]
            self._imap = mapping[1]
        else:
            mapping = cast(Dict, mapping)
            self._map: Dict = mapping
            self._imap: Dict = {v: k for k, v in mapping.items()}
        self.creation_kwargs['mapping'] = mapping

        if self._imap:
            self.modify_behavior('post_get', self.reverse_map_value.__func__,
                                 ('append',), 'reverse_map',  True)

        if self._map:
            self.modify_behavior('pre_set', self.map_value.__func__,
                                 ('append',), 'map', True)

    def reverse_map_value(self, driver: AbstractHasFeatures, value: Any
                          ) -> Any:
        return self._imap[value]

    def map_value(self, driver: AbstractHasFeatures, value: Any
                  ) -> Any:
        return self._map[value]
