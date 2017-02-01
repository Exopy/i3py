# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base class for VISA INstrument relying on text messages.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from inspect import cleandoc
from future.builtins import str

from pyvisa.rname import (ASRLInstr, GPIBInstr, TCPIPInstr, TCPIPSocket)
from pyvisa import errors

from ...core.util import byte_to_dict
from ...core.actions import Action

from .base import (BaseVisaDriver, VisaFeature, VisaAction,
                   get_visa_resource_manager)


class VisaMessageDriver(BaseVisaDriver):
    """Base class for driver communicating using VISA through text based
    messages.

    This covers among others GPIB, USB, TCPIP ...

    """
    #: The identification number of the manufacturer as hex code.
    #: :type: str | None
    MANUFACTURER_ID = None

    #: The code number of the model as hex code.
    #: Can provide a tuple/list to indicate multiple models.
    #: :type: str | list | tuple | None
    MODEL_CODE = None

    #: Meaning of the status byte.
    STATUS_BYTE = (0,
                   1,
                   2,
                   3,
                   'Message available',
                   'Event status',
                   'Request',
                   7)

    # XXX update once RegisterAction is finally there
    @Action()
    def read_status_byte(self):
        return byte_to_dict(self._resource.read_stb(), self.STATUS_BYTE)

    def default_get_feature(self, feat, cmd, *args, **kwargs):
        """Query the value using the provided command.

        The command is formatted using the provided args and kwargs before
        being passed on to the instrument.

        """
        return self._resource.query(cmd.format(*args, **kwargs))

    def default_set_feature(self, feat, cmd, *args, **kwargs):
        """Set the iproperty value of the instrument.

        The command is formatted using the provided args and kwargs before
        being passed on to the instrument.

        """
        return self._resource.write(cmd.format(*args, **kwargs))

    @classmethod
    def _via_usb(cls, resource_type='INSTR', serial_number=None,
                 manufacturer_id=None, model_code=None, board=0,
                 backend='default', caching_allowed=True, **kwargs):
        """Return a Driver with an underlying USB resource.

        A connected USBTMC instrument with the specified serial_number,
        manufacturer_id, and model_code is returned. If any of these is
        missing, the first USBTMC driver matching any of the provided values is
        returned.

        To specify the manufacturer id and/or the model code override the
        following class attributes::

            class RigolDS1052E(VisaMessageDriver):

                MANUFACTURER_ID = '0x1AB1'
                MODEL_CODE = '0x0588'

        Parameters
        ----------
        serial_number : str
            The serial number of the instrument.
        manufacturer_id : str
            The unique identification number of the manufacturer.
        model_code: str
            The unique identification number of the product.
        board: int
            USB Board to use.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """

        manufacturer_id = manufacturer_id or cls.MANUFACTURER_ID
        model_code = model_code or cls.MODEL_CODE

        if isinstance(model_code, (list, tuple)):
            _models = model_code
            model_code = '?*'
        else:
            _models = None

        query = 'USB{}::{}::{}::{}::?*::{}'.format(board,
                                                   manufacturer_id or '?*',
                                                   model_code or '?*',
                                                   serial_number or '?*',
                                                   resource_type)

        rm = get_visa_resource_manager(backend)
        try:
            resource_names = rm.list_resources(query)
        except errors.VisaIOError as e:
            msg = 'No USBTMC devices found for {} ({}).'.format(query, e)
            raise ValueError(msg)

        if _models:
            # There are more than 1 model compatible with
            resource_names = [r for r in resource_names
                              if r.split('::')[2] in _models]

        if not resource_names:
            msg = 'No USBTMC devices found for {} with model in {}'
            raise ValueError(msg.format(query, _models))

        if len(resource_names) > 1:
            msg = cleandoc('''{} USBTMC devices found for {}. Please specify
                           the serial number''')
            raise ValueError(msg.format(len(resource_names), query))

        return cls(resource_names[0], parameters=kwargs,
                   backend=backend, caching_allowed=caching_allowed)

    @classmethod
    def via_usb(cls, serial_number=None, manufacturer_id=None,
                model_code=None, board=0, backend='default',
                caching_allowed=True, **kwargs):
        """Return a Driver with an underlying USB Instrument resource.

        A connected USBTMC instrument with the specified serial_number,
        manufacturer_id, and model_code is returned. If any of these is
        missing, the first USBTMC driver matching any of the provided values is
        returned.

        To specify the manufacturer id and/or the model code override the
        following class attributes::

            class RigolDS1052E(VisaMessageDriver):

                MANUFACTURER_ID = '0x1AB1'
                MODEL_CODE = '0x0588'

        Parameters
        ----------
        serial_number : str
            The serial number of the instrument.
        manufacturer_id : str
            The unique identification number of the manufacturer.
        model_code: str
            The unique identification number of the product.
        board: int
            USB Board to use.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """

        return cls._via_usb('INSTR', serial_number, manufacturer_id,
                            model_code, board, backend, caching_allowed,
                            **kwargs)

    @classmethod
    def via_usb_raw(cls, serial_number=None, manufacturer_id=None,
                    model_code=None, board=0, backend='default',
                    caching_allowed=True,  **kwargs):
        """Return a Driver with an underlying USB RAW resource.

        Parameters
        ----------
        serial_number : str
            The serial number of the instrument.
        manufacturer_id : str
            The unique identification number of the manufacturer.
        model_code: str
            The unique identification number of the product.
        board: int
            USB Board to use.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """

        return cls._via_usb('RAW', serial_number, manufacturer_id, model_code,
                            board, backend, caching_allowed, **kwargs)

    @classmethod
    def via_serial(cls, board, backend='default', caching_allowed=True,
                   **kwargs):
        """Return a Driver with an underlying ASRL (Serial) Instrument resource.

        Parameters
        ----------
        port: int
            The serial port to which the instrument is connected.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        resource_name = ASRLInstr(board=board)
        return cls(str(resource_name), parameters=kwargs, backend=backend,
                   caching_allowed=caching_allowed)

    @classmethod
    def via_tcpip(cls, host_address, lan_device_name='inst0', board=0,
                  backend='default', caching_allowed=True, **kwargs):
        """Return a Driver with an underlying TCP Instrument resource.

        Parameters
        ----------
        hostaddress : str
            The ip address or hostname of the instrument.
        hostname: str, optional
            Name of the instrument....
        board: int, optional
            The board number.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver: VisaMessageDriver

        """
        rname = TCPIPInstr(**{'host_address': host_address,
                              'lan_device_name': lan_device_name,
                              'board': board})
        return cls(str(rname), parameters=kwargs, backend=backend,
                   caching_allowed=caching_allowed)

    @classmethod
    def via_tcpip_socket(cls, host_address, port, board=0,
                         backend='default', caching_allowed=True, **kwargs):
        """Return a Driver with an underlying TCP Socket resource.

        Parameters
        ----------
        hostaddress : str
            The ip address or hostname of the instrument.
        hostname: str, optional
            Name of the instrument....
        port : int
            The port of the instrument.
        board: int, optional
            The board number.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        rname = TCPIPSocket(**{'host_address': host_address,
                               'port': port,
                               'board': board})
        return cls(str(rname), parameters=kwargs, backend=backend,
                   caching_allowed=caching_allowed)

    @classmethod
    def via_gpib(cls, address, board=0, backend='default',
                 caching_allowed=True,
                 **kwargs):
        """Return a Driver with an underlying GPIB Instrument resource.

        Parameters
        ----------
        address : int
             The gpib address of the instrument.
        board : int, optional
            Number of the GPIB board.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs :
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        rname = GPIBInstr(board=board, primary_address=address)
        return cls(str(rname), parameters=kwargs, backend=backend,
                   caching_allowed=caching_allowed)

    # --- Pyvisa wrappers -----------------------------------------------------

    #: Encoding used for read and write operations.
    encoding = VisaFeature()

    #: Read termination character.
    read_termination = VisaFeature()

    #: Write termination character.
    write_termination = VisaFeature()

    @VisaAction()
    def write_raw(self, message):
        """See Pyvisa docs.

        """
        return self._resource.write_raw(message)

    @VisaAction()
    def write(self, message, termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self._resource.write(message, termination, encoding)

    @VisaAction()
    def write_ascii_values(self, message, values, converter='f', separator=',',
                           termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self._resource.write_ascii_values(message, values, converter,
                                                 separator, termination,
                                                 encoding)

    @VisaAction()
    def write_binary_values(self, message, values, datatype='f',
                            is_big_endian=False, termination=None,
                            encoding=None):
        """See Pyvisa docs.

        """
        return self._resource.write_binary_values(message, values, datatype,
                                                  is_big_endian, termination,
                                                  encoding)

    @VisaAction()
    def read_raw(self, size=None):
        """See Pyvisa docs.

        """
        return self._resource.read_raw(size)

    @VisaAction()
    def read(self, termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self._resource.read(termination, encoding)

    @VisaAction()
    def read_values(self, fmt=None, container=list):
        """See Pyvisa docs.

        """
        return self._resource.read_values(fmt, container)

    @VisaAction()
    def query(self, message, delay=None):
        """See Pyvisa docs.

        """
        with self.lock:
            return self._resource.query(message, delay)

    @VisaAction()
    def query_ascii_values(self, message, converter='f', separator=',',
                           container=list, delay=None):
        """See Pyvisa docs.

        """
        with self.lock:
            return self._resource.query_ascii_values(message, converter,
                                                     separator, container,
                                                     delay)

    @VisaAction()
    def query_binary_values(self, message, datatype='f', is_big_endian=False,
                            container=list, delay=None, header_fmt='ieee'):
        """See Pyvisa docs.

        """
        with self.lock:
            return self._resource.query_binary_values(message, datatype,
                                                      is_big_endian, container,
                                                      delay, header_fmt)

    @VisaAction()
    def assert_trigger(self):
        """Sends a software trigger to the device.

        """
        self._resource.assert_trigger()
