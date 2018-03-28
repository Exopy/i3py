# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Package for the drivers of ITest modules.

"""
import sys
from i3py.core.lazy_package import LazyPackage

DRIVERS = {}

sys.modules[__name__] = LazyPackage(DRIVERS, __name__, __doc__, locals())
