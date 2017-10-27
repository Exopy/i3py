# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by Pyvisa-I3py-sim Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Simulated backend for pyvisa based on i3py.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from .highlevel import I3pySimVisaLibrary
from .version import __version__

# XXX manually inject the backend in pyvisa
WRAPPER_CLASS = I3pySimVisaLibrary

