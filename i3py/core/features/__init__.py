# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Features are descriptor used for implementing instrument properties.

"""
from .feature import AbstractFeature, Feature
from .bool import Bool
from .scalars import Unicode, Int, Float
from .register import Register
from .alias import Alias
from .factories import constant, conditional

__all__ = ['AbstractFeature', 'Feature', 'Bool', 'Unicode', 'Int', 'Float',
           'Register', 'Alias', 'constant', 'conditional']
