# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Feature whose value is mapped to another Feature.

"""
from types import MethodType
from typing import Any, Dict, Callable

from ..abstracts import AbstractHasFeatures
from .feature import Feature, get_chain, set_chain


GET_DEF =\
"""def get(self, driver):
    return {}

"""


SET_DEF =\
"""def set(self, driver, value):
    {} = value

"""


class Alias(Feature):
    """Feature whose value is mapped to another Feature.

    Parameters
    ----------
    alias : str
        Path to the feature to which the alias refers to. The path should be
        dot separated and use leading dots to access to parent features.

    settable: bool, optional
        Boolean indicating if the alias can be used to set the value of the
        aliased feature.

    """

    def __init__(self, alias: str, settable: bool=False) -> None:

        super(Alias, self).__init__(True, settable if settable else None)

        accessor = 'driver.' + '.'.join([p if p else 'parent'
                                         for p in alias.split('.')])

        defs = GET_DEF.format(accessor)
        if settable:
            defs += '\n' + SET_DEF.format(accessor)

        loc: Dict[str, Callable] = {}
        exec(defs, globals(), loc)

        self.get = MethodType(loc['get'], self)  # type: ignore
        if settable:
            self.set = MethodType(loc['set'], self)  # type: ignore

    def post_set(self, driver: AbstractHasFeatures, value: Any, i_value: Any,
                 response: Any):
        """Re-implemented here as an Alias does not need to do anything
        by default.

        """
        pass

    # =========================================================================
    # --- Private API ---------------------------------------------------------
    # =========================================================================

    def _get(self, driver: AbstractHasFeatures):
        """Re-implemented so that Alias never use the cache.

        """
        with driver.lock:
            return get_chain(self, driver)

    def _set(self, driver: AbstractHasFeatures, value: Any):
        """Re-implemented so that Alias never uses the cache.

        """
        with driver.lock:
            set_chain(self, driver, value)
