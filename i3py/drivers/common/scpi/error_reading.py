# -*- coding: utf-8 -*-
"""
    lantz_drivers.common.scpi.error_reading
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Base driver for instrument implementing SCPI error reporting commands.


    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from lantz_core import Action
from lantz_core.backends.visa import VisaMessageDriver


class SCPIErrorReading(VisaMessageDriver):
    """Base class for all instruments implementing 'SYST:ERR?'.

    """

    @Action()
    def read_error(self):
        """Read the first error in the error queue.

        If an unhandle error occurs, the error queue should be polled till it
        is empty.

        """
        code, msg = self.query('SYST:ERR?').split(',')
        return int(code), msg

    def default_check_operation(self, feat, value, i_value, response):
        """Check if an error is present in the error queue.

        """
        code, msg = self.read_error()
        return bool(code), msg
