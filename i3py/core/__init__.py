# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""An instrumentation toolkit with a clean and consistent interface.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from .has_features import subsystem, channel, set_feat, set_action
from .errors import (I3pyError, InvalidCommand, TimeoutError,
                     InterfaceNotSupported)
from .limits import IntLimitsValidator, FloatLimitsValidator
from .unit import set_unit_registry, get_unit_registry

__all__ = ['subsystem', 'channel', 'set_action', 'set_feat',
           'I3pyError', 'InvalidCommand', 'TimeoutError',
           'InterfaceNotSupported', 'set_unit_registry', 'get_unit_registry',
           'IntLimitsValidator', 'FloatLimitsValidator']
