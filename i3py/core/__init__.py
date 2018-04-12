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
from .base_channel import Channel
from .base_subsystem import SubSystem
from .composition import customize
from .declarative import channel, limit, set_action, set_feat, subsystem
from .errors import (I3pyError, I3pyInterfaceNotSupported, I3pyInvalidCommand,
                     I3pyTimeoutError)
from .has_features import HasFeatures
from .job import InstrJob
from .limits import FloatLimitsValidator, IntLimitsValidator
from .unit import get_unit_registry, set_unit_registry

__all__ = ['subsystem', 'channel', 'set_action', 'set_feat', 'limit',
           'customize', 'I3pyError', 'I3pyInvalidCommand', 'I3pyTimeoutError',
           'I3pyInterfaceNotSupported',
           'set_unit_registry', 'get_unit_registry',
           'IntLimitsValidator', 'FloatLimitsValidator',
           'InstrJob', 'Channel', 'SubSystem', 'HasFeatures']
