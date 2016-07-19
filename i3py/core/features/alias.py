# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Feature whose value is mapped to another Feature.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from types import MethodType

from future.utils import exec_

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

    """

    def __init__(self, alias, settable=None):

        super(Alias, self).__init__(True, settable)

        accessor = 'driver.' + '.'.join([p if p else 'parent'
                                         for p in alias.split('.')])

        defs = GET_DEF.format(accessor)
        if settable:
            defs += '\n' + SET_DEF.format(accessor)

        loc = {}
        exec_(defs, globals(), loc)

        self.get = MethodType(loc['get'], self)
        if settable:
            self.set = MethodType(loc['set'], self)

    def post_set(self, driver, value, i_value, response):
        """Re-implemented here as an Alias does not need to do anaything
        by default.

        """
        pass

    # =========================================================================
    # --- Private API ---------------------------------------------------------
    # =========================================================================

    def _get(self, driver):
        """Re-implemented so that Alias never use the cache.

        """
        with driver.lock:
            return get_chain(self, driver)

    def _set(self, driver, value):
        """Re-implemented so that Alias never uses the cache.

        """
        with driver.lock:
            set_chain(self, driver, value)
