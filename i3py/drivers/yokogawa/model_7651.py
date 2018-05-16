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
from i3py.core import (set_feat, set_action, channel, subsystem,
                       limit, customize, FloatLimitsValidator, I3pyError)
from i3py.core.features import Str, conditional, constant
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
    - we should check the mode on startup (is it only possible ?)
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
        print(self.resource_name)
        try:
            super().initialize()
            # Choose the termination character
            self.visa_resource.write('DL0')
            # Unmask the status byte by default.
            self.visa_resource.write('MS31')
            # Clear the status byte
            self.read_status_byte()
        except Exception as e:
            raise I3pyError('Connection failed to open. One possible reason '
                            'is because the instrument is configured to write '
                            'on the memory card.') from e

    @RegisterAction(('program_setting',  # Program is currently edited
                     'program_execution',  # Program under execution
                     'error',  # Previous command error
                     'output_unstable',
                     'output_on',
                     'calibration mode',
                     'ic_memory_card',
                     'cal_switch'))
    def read_status_code(self):  # Should this live in a subsystem ?
        """Read the status code.

        """
        # The return format is STS1={value}
        return int(self.visa_resource.query('OC')[5:])

    read_status_byte = set_action(names=('end_of_output_change',
                                         'srq_key_on',
                                         'syntax_error',
                                         'limit_error',
                                         'program_end',
                                         'error',
                                         'request',
                                         None))

    def is_connected(self):
        """Check whether or not the connection is opened.

        """
        try:
            self.visa_resource.query('OC')
        except Exception:
            return False

        return True

    identity = subsystem(Identity)

    with identity as i:

        i.manufacturer = set_feat(getter=constant('Yokogawa'))

        i.model = set_feat(getter=True)

        i.serial = set_feat(getter=constant('xxx'))

        i.firmware = set_feat(getter=True)

        @i
        def _get_from_os(driver, index):
            """Read the requested info from OS command.

            """
            parser = Parser('MDL{}REV{}')
            visa_rsc = driver.parent.visa_resource
            mes = visa_rsc.query('OS')
            visa_rsc.read()
            visa_rsc.read()
            visa_rsc.read()
            visa_rsc.read()
            return parser(mes)[index]

        @i
        @customize('model', 'get')
        def _get_model(feat, driver):
            return driver._get_from_os(0)

        @i
        @customize('firmware', 'get')
        def _get_firmware(feat, driver):
            return driver._get_from_os(1)

    outputs = channel((0,))

    with outputs as o:
        o.mode = Str('OD', 'F{}E',
                     mapping=({'voltage': '1', 'current': '5'},
                              {'V': 'voltage', 'A': 'current'}),
                     extract='{_}DC{}{_:+E}',
                     discard={'features': ('enabled', 'voltage', 'current',
                                           'voltage_range', 'current_range'),
                              'limits': ('current', 'voltage')})

        o.enabled = set_feat(getter=True,
                             setter='O{}E',
                             mapping=({True: 1, False: 0}, None))

        o.voltage = set_feat(
            getter=True,
            setter=conditional('"S{:+E}E" if driver.mode == "voltage" '
                               'else "LV{:.0f}"', default=True),
            limits='voltage')

        o.voltage_range = set_feat(getter=True,
                                   setter='R{}E',
                                   extract='F1R{:d}S{_}',
                                   checks=(None, 'driver.mode == "voltage"'),
                                   mapping={10e-3: 2, 100e-3: 3, 1.0: 4,
                                            10.0: 5, 30.0: 6},
                                   discard={'features': ('current',),
                                            'limits': ('voltage',)})

        o.current = set_feat(getter=True,
                             setter=True,
                             limits='current')

        o.current_range = set_feat(getter=True,
                                   setter='R{}E',
                                   extract='F5R{:d}S{_}',
                                   checks=(None, 'driver.mode == "current"'),
                                   mapping={1e-3: 4, 10e-3: 5, 100e-3: 6},
                                   discard={'limits': ('current',)})

        @o
        @Action()
        def read_output_status(self):
            """Determine the status of the output.

            Returns
            -------
            status : str, {'disabled',
                           'enabled:constant-voltage',
                           'enabled:constant-voltage',
                           'tripped:unknown', 'unregulated'}

            """
            if not self.enabled:
                return 'disabled'
            sc = self.parent.read_status_code()
            if sc & sc.output_unstable:
                return 'unregulated'
            elif not (sc & sc.output_on):
                return 'tripped:unknown'
            if self.parent.visa_resource.query('OD')[0] == 'E':
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
            stb = self.parent.read_status_byte()
            if stb & stb.error:
                return False, ('Syntax error' if stb & stb.syntax_error else
                               'Limit error')

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
            if self.mode == 'current':
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
        def _get_enabled(feat, driver):
            """Read the output current status byte and extract the output state

            """
            sc = driver.parent.read_status_code()
            return bool(sc & sc.output_on)

        o._OD_PARSER = Parser('{_}DC{_}{:E+}')

        o._VOLT_LIM_PARSER = Parser('LV{}LA{_}')

        o._CURR_LIM_PARSER = Parser('LV{_}LA{}')

        @o
        @customize('voltage', 'get')
        def _get_voltage(feat, driver):
            """Get the voltage in voltage mode and return the maximum voltage
            in current mode.

            """
            if driver.mode != 'voltage':
                return driver._VOLT_LIM_PARSER(driver._get_limiter_value())
            return driver._OD_PARSER(driver.default_get_feature(feat, 'OD'))

        @o
        @customize('current', 'get')
        def _get_current(feat, driver):
            """Get the current in current mode and return the maximum current
            in voltage mode.

            """
            if driver.mode != 'voltage':
                if to_float(driver.voltage_range) in (10e-3, 100e-3):
                    return 0.12
                answer = driver._get_limiter_value()
                return float(driver._CURR_LIM_PARSER(answer))*1e3
            return driver._OD_PARSER(driver.default_get_feature(feat, 'OD'))

        @o
        @customize('current', 'set')
        def _set_current(feat, driver, value):
            """Set the target/limit current.

            In voltage mode this is only possible if the range is 1V or greater

            """
            if driver.mode != 'current':
                if to_float(driver.voltage_range) in (10e-3, 100e-3):
                    raise ValueError('Cannot set the current limit for ranges '
                                     '10mV and 100mV')
                else:
                    return driver.default_set_feature(feat, 'LA{:d}',
                                                      int(round(value*1e3)))
            return driver.default_set_feature(feat, 'S{:+E}E', value)

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

        @o
        def _get_range(driver, kind):
            """Read the range.

            """
            visa_rsc = driver.parent.visa_resource
            if driver.mode == kind:
                visa_rsc.write('OS')
                visa_rsc.read()  # Model and software version
                msg = visa_rsc.read()  # Function, range, output data
                visa_rsc.read()  # Program parameters
                visa_rsc.read()  # Limits
                return msg
            else:
                return 'F{}R6S1E+0'.format(1 if kind == 'voltage' else 5)

        @o
        @customize('voltage_range', 'get')
        def _get_voltage_range(feat, driver):
            return driver._get_range('voltage')

        @o
        @customize('current_range', 'get')
        def _get_current_range(feat, driver):
            return driver._get_range('current')
