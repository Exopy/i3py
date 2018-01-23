# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Simulated backend for pyvisa based on i3py.

"""
from i3py.core.highlevel import I3pySimVisaLibrary
from i3py.version import __version__

# XXX manually inject the backend in pyvisa
WRAPPER_CLASS = I3pySimVisaLibrary

