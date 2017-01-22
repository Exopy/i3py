# -*- coding: utf-8 -*-
"""
    lantz_drivers.yokogawa.model_7651
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Driver for the Yokogawa 7651 DC power source.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from functools import partial

from lantz_core import (set_feat, channel, conditional, Action, subsystem)
from lantz_core.limits import FloatLimitsValidator
from lantz_core.utils import byte_to_dict
from lantz_core.unit import to_float
from lantz_core.backends.visa import VisaMessageDriver
from stringparser import Parser

from ..base.dc_sources import DCPowerSource
from ..base.identity import Identity


VOLTAGE_RESOLUTION = {10e-3: 1e-7,
                      100e-3: 1e-6,
                      1.0: 1e-5,
                      10: 1e-4,
                      30: 1e-3}

CURRENT_RESOLUTION = {1e-3: 1e-8,
                      10e-3: 1e-7,
                      100e-3: 1e-6}


class Yokogawa7651(VisaMessageDriver, DCPowerSource):
    """Driver for the Yokogawa 7651 DC power source.

    This driver can also be used on Yokogawa GS200 used in compatibility mode.

    """
    PROTOCOLS = {'GPIB': 'INSTR'}

    DEFAULTS = {'COMMON': {'read_termination': '\r\n'},
                'ASRL': {'write_termination': '\r\n'}}

    STATUS_BYTE = ('End of output change',
                   'SRQ key on',
                   'Syntax error',
                   'Limit error',
                   'Program end',
                   'Error',
                   'Request',
                   7)

    def initialize(self):
        """Set the data termination.

        """
        super(Yokogawa7651, self).initialize()
        self.write('DL0')  # Choose the termination character
        self.write('MS31')  # Unmask the status byte by default.

    @Action()
    def read_status_code(self):  # Should this live in a subsystem ?
        """Read the status code.

        """
        return byte_to_dict(self.query('OC'),
                            ('Program setting',  # Program is currently edited
                             'Program execution',  # Program under execution
                             'Error',  # Previous command error
                             'Output unustable',
                             'Output on',
                             'Calibration mode',
                             'IC memory card',
                             'CAL switch'))

    @property
    def connected(self):
        """Check whether or not the connection is opened.

        """
        try:
            self.query('OC')
        except Exception:
            return False

        return True

    identity = subsystem(Identity)

    with identity as i:

        i.model = set_feat(getter=True)

        i.firmware = set_feat(getter=True)

        @i
        def _get_from_os(index, self):
            """Read the requested info from OS command.

            """
            mes = self.parent.query('OS')
            self.parent.read()
            self.parent.read()
            self.parent.read()
            self.parent.read()
            return mes.split(',')[index]

        i._get_model = partial(0, i._get_from_os)

        i._get_firmware = partial(1, i._get_from_os)

    output = channel()

    with output as o:
        o.function = set_feat(getter='OD',
                              setter='F{}E',
                              mapping=({'Voltage': '1', 'Current': '5'},
                                       {'V': 'Voltage', 'A': 'Current'}),
                              extract='{_}DC{}{_:+E}')

        o.enabled = set_feat(getter=True,
                             setter='O{}E',
                             mapping={True: 1, False: 0})

        o.voltage = set_feat(
            getter=True,
            setter=conditional('"S{+E}E" if driver.mode == "voltage" '
                               'else "LV{}E"', default=True),
            limits='voltage')

        o.voltage_range = set_feat(getter=True,
                                   setter='R{}E',
                                   extract='F1R{}S{_}',
                                   mapping={10e-3: 2, 100e-3: 3, 1.0: 4,
                                            10.0: 5, 30.0: 6},
                                   discard={'features': ('current'),
                                            'limits': ('voltage',)})

        o.current = set_feat(getter=True,
                             setter=True,
                             limits='current')

        o.current_range = set_feat(getter=True,
                                   setter='R{}E',
                                   extract='F5R{}S{_}',
                                   mapping={1e-3: 4, 10e-3: 5, 100e-3: 6},
                                   discard={'limits': ('current',)})

        @o
        @Action()
        def read_output_status(self):
            """Determine the status of the output.

            Returns
            -------
            status : unicode, {'disabled',
                               'constant voltage', 'constant voltage',
                               'tripped', 'unregulated'}

            """
            if not self.enabled:
                return 'disabled'
            if 'Output on' not in self.read_status_code():
                return 'tripped'
            if self.parent.query('OD')[0] == 'E':
                if self.mode == 'voltage':
                    return 'constant current'
                else:
                    return 'constant voltage'
            if self.mode == 'voltage':
                return 'constant voltage'
            else:
                return 'constant current'

        # =====================================================================
        # --- Private API -----------------------------------------------------
        # =====================================================================

        @o
        def default_check_operation(self, feat, value, i_value, state=None):
            """Check that the operation did not result in any error.

            """
            stb = self.parent.read_status_byte()
            if stb['Syntax error']:
                msg = 'Syntax error' if stb['Limit error'] else 'Overload'
                return False, msg

            return True, None

        @o
        def _limits_voltage(self):
            """Determine the voltage limits based on the currently selected
            range.

            """
            if self.mode == 'voltage':
                ran = to_float(self.voltage_range)
                res = VOLTAGE_RESOLUTION[ran]
                if ran != 30.0:
                    ran *= 1.2
                else:
                    ran = 32.0
                return FloatLimitsValidator(-ran, ran, res, 'V')
            else:
                return FloatLimitsValidator(1, 30, 1, 'V')

        @o
        def _limits_current(self):
            """Determine the current limits based on the currently selected
            range.

            """
            if self.mode == 'voltage':
                ran = float(self.current_range)  # Casting handling Quantity
                res = CURRENT_RESOLUTION[ran]
                if ran != 200e-3:
                    ran *= 1.2
                else:
                    ran = 220e-3
                return FloatLimitsValidator(-ran, ran, res, 'A')
            else:
                return FloatLimitsValidator(5e-3, 120e-3, 1e-3, 'A')

        @o
        def _get_enabled(self):
            """Read the output current status byte and extract the output state

            """
            return 'Output' in self.parent.read_status_code()

        o._OD_PARSER = Parser('{_}DC{_}{:E+}')

        o._VOLT_LIM_PARSER = Parser('LV{}LA{_}')

        o._CURR_LIM_PARSER = Parser('LV{_}LA{}')

        @o
        def _get_voltage(self, feat):
            """Get the voltage in voltage mode and return the maximum voltage
            in current mode.

            """
            if self.mode != 'voltage':
                return self._VOLT_LIM_PARSER(self._get_limiter_value())
            return self._OD_PARSER(self.default_get_feature('OD'))

        @o
        def _get_current(self, feat):
            """Get the current in current mode and return the maximum current
            in voltage mode.

            """
            if self.mode != 'voltage':
                if to_float(self.voltage_range) in (10e-3, 100e-3):
                    return 0.12
                return self._CURR_LIM_PARSER(self._get_limiter_value())*1e3
            return self._OD_PARSER(self.default_get_feature('OD'))

        @o
        def _set_current(self, feat, value):
            """Set the target/limit current.

            In voltage mode this is only possible if the range is 1V or greater

            """
            if self.mode != 'current':
                if to_float(self.voltage_range) in (10e-3, 100e-3):
                    raise ValueError('Cannot set the current limit for ranges '
                                     '10mV and 100mV')
                else:
                    return self.default_set_feature('LA{}E', value)
            return self.default_set_feature('S{+E}E', value)

        @o
        def _get_limiter_value(self):
            """Read the limiter value.

            """
            self.write('OS')
            self.read()  # Model and software version
            self.read()  # Function, range, output data
            self.read()  # Program parameters
            return self.read()  # Limits

        @o
        def _get_range(kind, self):
            """Read the range.

            """
            if self.mode == kind:
                self.write('OS')
                self.read()  # Model and software version
                msg = self.read()  # Function, range, output data
                self.read()  # Program parameters
                self.read()  # Limits
                return msg
            else:
                return 'F{}R6S1E+0'.format(1 if kind == 'voltage' else 5)

        o._get_voltage_range = partial(o._get_range, 'voltage')

        o._get_current_range = partial(o._get_range, 'current')
