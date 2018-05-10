# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Driver for the Yokogawa 7651 DC power source.

"""
from functools import partial

from i3py.core import (set_feat, set_action, channel, subsystem,
                       limit, customize, FloatLimitsValidator)
from i3py.core.features import conditional
from i3py.core.unit import to_float
from i3py.core.actions import Action, RegisterAction
from i3py.backends.visa import VisaMessageDriver
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


class Model7651(VisaMessageDriver, DCPowerSource):
    """Driver for the Yokogawa 7651 DC power source.

    This driver can also be used on Yokogawa GS200 used in compatibility mode.

    XXX add motivation for use of limits

    Notes
    -----
    - we should check the mode on startup
    - ideally we should not keep the VisaSession opened on GPIB
    - add support for programs
    - add RS232 support

    """
    __version__ = '0.1.0'

    PROTOCOLS = {'GPIB': [{'resource_class': 'INSTR'}]}

    DEFAULTS = {'COMMON': {'read_termination': '\r\n'},
                'ASRL': {'write_termination': '\r\n'}}

    def initialize(self):
        """Set the data termination.

        """
        super().initialize()
        self.visa_resource.write('DL0')  # Choose the termination character
        self.visa_resource.write('MS31')  # Unmask the status byte by default.

    @RegisterAction(('Program setting',  # Program is currently edited
                     'Program execution',  # Program under execution
                     'Error',  # Previous command error
                     'Output unustable',
                     'Output on',
                     'Calibration mode',
                     'IC memory card',
                     'CAL switch'))
    def read_status_code(self):  # Should this live in a subsystem ?
        """Read the status code.

        """
        return int(self.visa_resource.query('OC'))

    read_status_byte = set_action(names=('End of output change',
                                         'SRQ key on',
                                         'Syntax error',
                                         'Limit error',
                                         'Program end',
                                         'Error',
                                         'Request',
                                         7))

    def is_connected(self):
        """Check whether or not the connection is opened.

        """
        try:
            self.visa.resource.query('OC')
        except Exception:
            return False

        return True

    identity = subsystem(Identity)

    with identity as i:

        i.model = set_feat(getter=True)

        i.firmware = set_feat(getter=True)

        def _get_from_os(index, self):
            """Read the requested info from OS command.

            """
            visa_rsc = self.parent.visa_resource
            mes = visa_rsc.query('OS')
            visa_rsc.read()
            visa_rsc.read()
            visa_rsc.read()
            visa_rsc.read()
            return mes.split(',')[index]

        i._get_model = customize('model', 'get')(partial(0, i._get_from_os))

        i._get_firmware = customize('model', 'get')(partial(1, i._get_from_os))

    output = channel((1,))

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
                               'enabled:constant-voltage',
                               'enabled:constant-voltage',
                               'tripped:unknown', 'unregulated'}

            """
            if not self.enabled:
                return 'disabled'
            if 'Output on' not in self.parent.read_status_code():
                return 'tripped:unknown'
            if self.parent.query('OD')[0] == 'E':
                if self.mode == 'voltage':
                    return 'enabled:constant-current'
                else:
                    return 'enabled:constant-voltage'
            if self.mode == 'voltage':
                return 'enabled:constant-voltage'
            else:
                return 'enabled:constant-current'

        # =====================================================================
        # --- Private API -----------------------------------------------------
        # =====================================================================

        @o
        def default_check_operation(self, feat, value, i_value, state=None):
            """Check that the operation did not result in any error.

            """
            stb = self.parent.visa_resource.read_status_byte()
            if stb['Syntax error']:
                msg = 'Syntax error' if stb['Limit error'] else 'Overload'
                return False, msg

            return True, None

        @o
        @limit('voltage')
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
        @limit('current')
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
        @customize('enabled', 'get')
        def _get_enabled(self):
            """Read the output current status byte and extract the output state

            """
            return 'Output' in self.parent.read_status_code()

        o._OD_PARSER = Parser('{_}DC{_}{:E+}')

        o._VOLT_LIM_PARSER = Parser('LV{}LA{_}')

        o._CURR_LIM_PARSER = Parser('LV{_}LA{}')

        @o
        @customize('voltage', 'get')
        def _get_voltage(self, feat):
            """Get the voltage in voltage mode and return the maximum voltage
            in current mode.

            """
            if self.mode != 'voltage':
                return self._VOLT_LIM_PARSER(self._get_limiter_value())
            return self._OD_PARSER(self.default_get_feature('OD'))

        @o
        @customize('current', 'get')
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
        @customize('current', 'set')
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
            """Helper function reading the limiter value.

            Used to read the voltage/current target.

            """
            visa_rsc = self.parent.visa_resource
            visa_rsc.write('OS')
            visa_rsc.read()  # Model and software version
            visa_rsc.read()  # Function, range, output data
            visa_rsc.read()  # Program parameters
            return visa_rsc.read()  # Limits

        def _get_range(kind, self):
            """Read the range.

            """
            visa_rsc = self.parent.visa_resource
            if self.mode == kind:
                visa_rsc.write('OS')
                visa_rsc.read()  # Model and software version
                msg = visa_rsc.read()  # Function, range, output data
                visa_rsc.read()  # Program parameters
                visa_rsc.read()  # Limits
                return msg
            else:
                return 'F{}R6S1E+0'.format(1 if kind == 'voltage' else 5)

        o._get_voltage_range = customize('voltage_range',
                                         'get')(partial(_get_range, 'voltage'))

        o._get_current_range = customize('current_range',
                                         'get')(partial(_get_range, 'current'))
