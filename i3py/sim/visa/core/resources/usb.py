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


@sessions.Session.register(constants.InterfaceType.usb, 'INSTR')
class USBInstrumentSession(sessions.Session):
    """Session for USB INSTR instruments.

    """

    def __init__(self, resource_manager_session, resource_name, parsed):
        super(USBInstrumentSession, self).__init__(resource_manager_session,
                                                   resource_name, parsed)

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed.board)
        self.attrs[constants.VI_ATTR_MANF_ID] = self.parsed.manufacturer_id
        self.attrs[constants.VI_ATTR_MODEL_CODE] = self.parsed.model_code
        self.attrs[constants.VI_ATTR_USB_SERIAL_NUM] =\
            self.parsed.serial_number
        self.attrs[constants.VI_ATTR_USB_INTFC_NUM] = int(self.parsed.board)

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


@sessions.Session.register(constants.InterfaceType.usb, 'RAW')
class USBRawSession(sessions.Session):
    """Session for USB RAW instruments.

    """

    def __init__(self, resource_manager_session, resource_name, parsed):
        super(USBRawSession, self).__init__(resource_manager_session,
                                            resource_name, parsed)

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed.board)
        self.attrs[constants.VI_ATTR_MANF_ID] = self.parsed.manufacturer_id
        self.attrs[constants.VI_ATTR_MODEL_CODE] = self.parsed.model_code
        self.attrs[constants.VI_ATTR_USB_SERIAL_NUM] =\
            self.parsed.serial_number
        self.attrs[constants.VI_ATTR_USB_INTFC_NUM] = int(self.parsed.board)

    def read(self, count):
        end_char, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR)
        enabled, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR_EN)
        timeout, _ = self.get_attribute(constants.VI_ATTR_TMO_VALUE)
        timeout /= 1000

        now = start = time.time()

        out = b''
        tc_success = constants.StatusCode.success_termination_character_read

        while now - start <= timeout:
            last = self.device.read()

            if not last:
                time.sleep(.01)
                now = time.time()
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
