# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test that the version script is functional.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from i3py import version

assert version.__version__
