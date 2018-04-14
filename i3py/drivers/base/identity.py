# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Standard interface of the identity subsystem.

"""
from i3py.core.base_subsystem import SubSystem
from i3py.core.features import Str


class Identity(SubSystem):
    """Standard subsystem defining the expected identity info.

    This should be used as a base class for the identity subsystem of
    instruments providing identity information.

    Notes
    -----
    Some of those info might not be available for a given instrument. In such
    a case the Feature should return ''.

    """
    #: Manufacturer as returned by the instrument.
    manufacturer = Str(True)

    #: Model name as returned by the instrument.
    model = Str(True)

    #: Instrument serial number.
    serial = Str(True)

    #: Version of the installed firmware.
    firmware = Str(True)
