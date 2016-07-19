# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Features are descriptor used for implementing instrument properties.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from .feature import AbstractFeature, Feature
from .bool import Bool
from .scalars import Unicode, Int, Float
from .register import Register
from .alias import Alias
from .util import constant, conditional

__all__ = ['AbstractFeature', 'Feature', 'Bool', 'Unicode', 'Int', 'Float',
           'Register', 'Alias', 'constant', 'conditional']
