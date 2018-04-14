# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Package for the drivers of Itest instruments.

"""
import sys
from i3py.core.lazy_package import LazyPackage

DRIVERS = {'BN100': 'racks.BN100', 'BN101': 'racks.BN101',
           'BN103': 'racks.BN103', 'BN105': 'racks.BN105'}

sys.modules[__name__] = LazyPackage(DRIVERS, __name__, __doc__, locals())
