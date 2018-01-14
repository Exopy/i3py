# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Core package of i3py defining the tools used to write the drivers.

"""
from .declarative import subsystem, channel, set_feat, set_action, limit
from .composition import customize
from .errors import (I3pyError, I3pyInvalidCommand, I3pyTimeoutError,
                     I3pyInterfaceNotSupported)
from .limits import IntLimitsValidator, FloatLimitsValidator
from .unit import set_unit_registry, get_unit_registry
from .job import InstrJob

__all__ = ['subsystem', 'channel', 'set_action', 'set_feat', 'limit',
           'customize', 'I3pyError', 'I3pyInvalidCommand', 'I3pyTimeoutError',
           'I3pyInterfaceNotSupported',
           'set_unit_registry', 'get_unit_registry',
           'IntLimitsValidator', 'FloatLimitsValidator',
           'InstrJob']
