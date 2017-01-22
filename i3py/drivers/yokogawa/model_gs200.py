# -*- coding: utf-8 -*-
"""
    lantz_drivers.yokogawa.model_gs200
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Driver for the Yokogawa GS200 DC power source.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from lantz_core import (set_feat, channel, Action)
from lantz_core.limits import FloatLimitsValidator
from lantz_core.features import Unicode, conditional
from lantz_core.unit import to_float

from ..base.dc_sources import DCPowerSource
from ..common.ieee488 import (IEEEInternalOperations, IEEEStatusReporting,
                              IEEEOperationComplete, IEEEOptionsIdentification,
                              IEEEStoredSettings)
from ..common.scpi.error_reading import SCPIErrorReading

VOLTAGE_RESOLUTION = {10e-3: 1e-7,
                      100e-3: 1e-6,
                      1.0: 1e-5,
                      10: 1e-4,
                      30: 1e-3}

CURRENT_RESOLUTION = {1e-3: 1e-8,
                      10e-3: 1e-7,
                      100e-3: 1e-6,
                      200e-3: 1e-6}


class YokogawaGS200(DCPowerSource, IEEEInternalOperations,
                    IEEEStatusReporting, IEEEOperationComplete,
                    IEEEOptionsIdentification, IEEEStoredSettings,
                    SCPIErrorReading):
    """Driver for the Yokogawa GS200 DC power source.

    """
    PROTOCOLS = {'GPIB': 'INSTR', 'USB': 'INSTR', 'TCPIP': 'INSTR'}

    DEFAULTS = {'COMMON': {'read_termination': '\n',
                           'write_termination': '\n'}}

    MANUFACTURER_ID = 0xB21

    MODEL_CODE = 0x39

    output = channel()

    with output as o:
        #: Preferential working mode for the source. In voltage mode, the
        #: source tries to work as a voltage source, the current settings is
        #: simply used to protect the sample. In current mode it is the
        #: opposite. Changing the mode cause the output to be disabled.
        o.mode = Unicode(getter=':SOUR:FUNC?',
                         setter=':SOUR:FUNC {}',
                         mapping={'voltage': 'VOLT', 'current': 'CURR'},
                         discard={'feature': ('enabled',
                                              'voltage', 'voltage_range',
                                              'current', 'current_range'),
                                  'limits': ('voltage', 'current')})

        o.voltage = set_feat(
            getter=conditional('":SOUR:LEV?" if driver.mode == "voltage" '
                               'else ":SOUR:PROT:VOLT?"', default=True),
            setter=conditional('":SOUR:LEV {}" if self.mode == "voltage" '
                               'else ":SOUR:PROT:VOLT {}"', default=True),
            limits='voltage')

        o.voltage_range = set_feat(getter=True,
                                   setter=':SOUR:RANG {}',
                                   checks=(None, 'driver.mode == "voltage"'),
                                   values=(10e-3, 100e-3, 1.0, 10.0, 30.0),
                                   discard={'features': ('ocp.enabled',
                                                         'ocp.high_level'),
                                            'limits': ('voltage',)})

        o.voltage_limit_behavior = set_feat(getter=conditional(
            '"regulate" if self.mode=="current" else "irrelevant"'))

        o.current = set_feat(getter=True,
                             setter=True,
                             limits='current')

        o.current_range = set_feat(getter=True,
                                   setter=':SOUR:RANG {}',
                                   values=(1e-3, 10e-3, 100e-3, 200e-3),
                                   discard={'limits': 'current'})

        o.voltage_limit_behavior = set_feat(getter=conditional(
            '"irrelevant" if self.mode=="current" else "regulate"'))

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
            event = int(self.query(':STAT:EVENT?:'))
            if event & 2**12:
                self.clear_cache(features=('enabled'))
                return 'tripped'
            elif (event & 2**11) or (event & 2**10):
                if self.mode == 'voltage':
                    return 'constant current'
                else:
                    return 'constant voltage'
            else:
                if self.mode == 'voltage':
                    return 'constant voltage'
                else:
                    return 'constant current'

        # =====================================================================
        # --- Private API -----------------------------------------------------
        # =====================================================================

        @o
        def _get_current(self, feat):
            """Get the target/limit current.

            """
            if self.mode != 'current':
                if to_float(self.voltage_range) in (10e-3, 100e-3):
                    return 0.2
                else:
                    return self.default_get_feature(':SOUR:PROT:CURR?')
            return self.default_get_feature(':SOUR:LEV?')

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
                    return self.default_set_feature(':SOUR:PROT:CURR {}',
                                                    value)
            return self.default_set_feature(':SOUR:LEV {}', value)

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
            if self.mode == 'current':
                ran = to_float(self.current_range)  # Casting handling Quantity
                res = CURRENT_RESOLUTION[ran]
                if ran != 200e-3:
                    ran *= 1.2
                else:
                    ran = 220e-3
                return FloatLimitsValidator(-ran, ran, res, 'A')
            else:
                return FloatLimitsValidator(1e-3, 0.2, 1e-3, 'A')
