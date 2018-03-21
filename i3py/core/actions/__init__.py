# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Actions are used to wrap method and mark them as acting on the instrument.

"""
from .action import BaseAction, Action
from .register_action import RegisterAction

__all__ = ['BaseAction', 'Action', 'RegisterAction']
