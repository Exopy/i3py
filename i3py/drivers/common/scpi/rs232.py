# -*- coding: utf-8 -*-
"""
    lantz_drivers.common.scpi.rs232
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Driver for the keysight E3631A DC power source.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from ..rs232 import VisaRS232


class SCPIRS232(VisaRS232):
    """Base class for SCPI compliant instruments supporting the RS232 protocol.

    """

    RS232_HEADER = 'SYST:REM;:'
