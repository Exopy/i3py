# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Session for TCPIP instruments.

"""
import time

from pyvisa import constants

from . import sessions


class BaseTCPIPSession(sessions.Session):
    """Base class for TCPIP sessions.

    """

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
            # EOM 4882
            pass


@sessions.Session.register(constants.InterfaceType.tcpip, 'INSTR')
class TCPIPInstrumentSession(BaseTCPIPSession):
    """Session for TCPIP INSTR instruments.

    """

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed.board)
        self.attrs[constants.VI_ATTR_TCPIP_ADDR] = self.parsed.host_address
        self.attrs[constants.VI_ATTR_TCPIP_DEVICE_NAME] =\
            self.parsed.lan_device_name


@sessions.Session.register(constants.InterfaceType.tcpip, 'SOCKET')
class TCPIPSocketSession(BaseTCPIPSession):
    """Session for TCPIP SOCKET instruments.

    """

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed.board)
        self.attrs[constants.VI_ATTR_TCPIP_ADDR] = self.parsed.host_address
        self.attrs[constants.VI_ATTR_TCPIP_PORT] = int(self.parsed.port)
