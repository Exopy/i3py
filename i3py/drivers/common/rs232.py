# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base class for driver supporting the VISA RS232 communication protocol.

This class ensures that the instrument is always in remote mode before
sending any other command.

"""
from types import MethodType

from i3py.backends.visa import VisaMessageDriver
from pyvisa.resources.serial import SerialInstrument


class VisaRS232(VisaMessageDriver):
    """Base class for all instruments supporting the RS232 interface.

    The specifity of the RS232 interface is that the device need to be switched
    to remote mode before sending any command. This class wrapps the low-level
    write method of the ressource when the connection is opened in RS232 mode
    and prepend the RS232_HEADER string to the message.

    """

    #:
    RS232_HEADER = None

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
