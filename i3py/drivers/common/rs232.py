# -*- coding: utf-8 -*-
"""
    lantz_drivers.common.rs232
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Base class for driver supporting the VISA RS232 communication protocol.

    This class ensures that the instrument is always in remote mode before
    sending any other command.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from types import MethodType

from lantz_core.backends.visa import VisaMessageDriver
from pyvisa.resources.serial import SerialInstrument


class VisaRS232(VisaMessageDriver):
    """Base class for all instruments supporting the RS232 interface.

    The specifity of the RS232 interface is that the device need to be switched
    to remote mode before sending any command. This class wrapps the low-level
    write method of the ressource when the connection is opened in RS232 mode
    and prepend the RS232_HEADER string to the message.

    """

    def initialize(self):
        """Initialize the driver and if pertinent wrap low level so that
        RS232_HEADER is prepended to messages.

        """
        super(VisaRS232, self).initialize()
        if isinstance(self._resource, SerialInstrument) and self.RS232_HEADER:
            write = self._resource.write.__func__

            def new_write(self, message, termination=None, encoding=None):
                return write(self, self.RS232_HEADER+message, termination,
                             encoding)
            self._resource.write = MethodType(new_write, self._resource)

            # XXX should do the same for write_ascii_values ?
            # XXX should do the same for write_binary_values ?
