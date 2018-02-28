# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Session for GPIB instruments.

"""
import time

from pyvisa import constants

from . import sessions


@sessions.Session.register(constants.InterfaceType.gpib, 'INSTR')
class GPIBInstrumentSession(sessions.Session):
    """Session for GPIB INSTR resources.

    """

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed.board)
        self.attrs[constants.VI_ATTR_GPIB_PRIMARY_ADDR] =\
            int(self.parsed.primary_address)
        self.attrs[constants.VI_ATTR_GPIB_SECONDARY_ADDR] =\
            int(self.parsed.secondary_address)

    def read(self, count):
        end_char, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR)
        enabled, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR_EN)
        timeout, _ = self.get_attribute(constants.VI_ATTR_TMO_VALUE)
        timeout /= 1000

        start = time.time()

        out = b''

        tc_success = constants.StatusCode.success_termination_character_read
        while time.time() - start <= timeout:
            last = self.device.read()

            if not last:
                time.sleep(.01)
                continue

            out += last

            if enabled:
                if len(out) > 0 and out[-1] == end_char:
                    return out, tc_success

            if len(out) == count:
                return out, constants.StatusCode.success_max_count_read
        else:
            return out, constants.StatusCode.error_timeout

    def write(self, data):
        send_end = self.get_attribute(constants.VI_ATTR_SEND_END_EN)

        for i in range(len(data)):
            self.device.write(data[i:i+1])

        if send_end:
            # EOM4882
            pass
