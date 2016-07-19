# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Feature for boolean like values.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

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
    def __init__(self, getter=None, setter=None, mapping=None, aliases=None,
                 extract='', retries=0, checks=None, discard=None, ):
        Mapping.__init__(self, getter, setter, mapping, extract,
                         retries, checks, discard)

        self._aliases = {True: True, False: False}
        if aliases:
            for k in aliases:
                for v in aliases[k]:
                    self._aliases[v] = k
        self.creation_kwargs['aliases'] = aliases

    def map_value(self, instance, value):
        self._aliases[value]
        return self._map[self._aliases[value]]
