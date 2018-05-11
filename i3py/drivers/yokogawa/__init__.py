# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Package for the drivers of Yokogawa instruments.

"""
import sys
from i3py.core.lazy_package import LazyPackage

DRIVERS = {'GS200': 'gs200.GS200', 'Model7651': 'model_7651.Model7651'}

sys.modules[__name__] = LazyPackage(DRIVERS, __name__, __doc__, locals())
