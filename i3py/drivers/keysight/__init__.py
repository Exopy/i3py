# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Package for the drivers of Keysight/Agilent/HP instruments.

"""
import sys
from i3py.core.lazy_package import LazyPackage

DRIVERS = {'E3631A': 'E363XA.E3631A', 'E3633A': 'E363XA.E3633A',
           'E3634A': 'E363XA.E3634A'}

sys.modules[__name__] = LazyPackage(DRIVERS, __name__, __doc__, locals())
