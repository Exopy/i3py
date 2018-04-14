# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base class for SCPI instruments supporting RS232-based communication.

"""
from ..rs232 import VisaRS232


class SCPIRS232(VisaRS232):
    """Base class for SCPI compliant instruments supporting the RS232 protocol.

    """

    RS232_HEADER = b'SYST:REM:;'
