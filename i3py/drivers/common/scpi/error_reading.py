# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base driver for instrument implementing SCPI error reporting commands.

"""
from typing import Tuple

from i3py.core.actions import Action
from i3py.backends.visa import VisaMessageDriver


class SCPIErrorReading(VisaMessageDriver):
    """Base class for all instruments implementing 'SYST:ERR?'.

    """

    @Action()
    def read_error(self) -> Tuple[int, str]:
        """Read the first error in the error queue.

        If an unhandled error occurs, the error queue should be polled till it
        is empty.

        """
        code, msg = self.visa_resource.query('SYST:ERR?').split(',', 1)
        return int(code), msg

    def default_check_operation(self, feat, value, i_value, response):
        """Check if an error is present in the error queue.

        """
        code, msg = self.read_error()
        return not bool(code), msg
