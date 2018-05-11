# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Driver for the Yokogawa GS200 DC power source.

"""
from i3py.core import (set_feat, channel, limit, customize,
                       FloatLimitsValidator)
from i3py.core.actions import Action
from i3py.core.features import Str, conditional, constant
from i3py.core.unit import to_float

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


class GS200(DCPowerSource, IEEEInternalOperations,
            IEEEStatusReporting, IEEEOperationComplete,
            IEEEOptionsIdentification, IEEEStoredSettings,
            SCPIErrorReading):
    """Driver for the Yokogawa GS200 DC power source.

    Notes
    -----
    - the measurement option is not yet supported.
    - add support for programs
    - add RS232 support

    XXX add motivation for use of limits (basically always enabled and behave
    just like a target value)
    XXX proper format for IDN

    """
    __version__ = '0.1.0'

    PROTOCOLS = {'GPIB': [{'resource_class': 'INSTR'}],
                 'USB': [{'resource_class': 'INSTR',
                          'manufacturer_id': '0xB21',
                          'model_code': '0x39'}],
                 'TCPIP': [{'reource_class': 'INSTR'}]
                 }

    DEFAULTS = {'COMMON': {'read_termination': '\n',
                           'write_termination': '\n'}}

    identity = subsystem()

    with identity as i:

        #: Format string specifying the format of the IDN query answer and
        #: allowing to extract the following information:
        #: - manufacturer: name of the instrument manufacturer
        #: - model: name of the instrument model
        #: - serial: serial number of the instrument
        #: - firmware: firmware revision
        #: ex {manufacturer},<{model}>,SN{serial}, Firmware revision {firmware}
        i.IEEE_IDN_FORMAT = ''

    output = channel((0,))

    with output as o:
        #: Preferential working mode for the source. In voltage mode, the
        #: source tries to work as a voltage source, the current settings is
        #: simply used to protect the sample. In current mode it is the
        #: opposite. Changing the mode cause the output to be disabled.
        o.mode = Str(getter=':SOUR:FUNC?',
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

        o.voltage_limit_behavior = set_feat(getter=constant("regulate"))

        o.current = set_feat(getter=True,
                             setter=True,
                             limits='current')

        o.current_range = set_feat(getter=True,
                                   setter=':SOUR:RANG {}',
                                   values=(1e-3, 10e-3, 100e-3, 200e-3),
                                   discard={'limits': 'current'})

        o.voltage_limit_behavior = set_feat(getter=constant("regulate"))

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
            event = int(self.root.visa_resource.query(':STAT:EVENT?:'))
            if event & 2**12:
                del self.enabled
                return 'tripped:unknown'
            elif (event & 2**11) or (event & 2**10):
                if self.mode == 'voltage':
                    return 'enabled:constant-current'
                else:
                    return 'enabled:constant-voltage'
            else:
                if self.mode == 'voltage':
                    return 'enabled:constant-voltage'
                else:
                    return 'enabled:constant-current'

        # TODO add support for options and measuring subsystem (change
        # inheritance)

        # =====================================================================
        # --- Private API -----------------------------------------------------
        # =====================================================================

        @o
        @customize('current', 'get')
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
                    return self.default_set_feature(':SOUR:PROT:CURR {}',
                                                    value)
            return self.default_set_feature(':SOUR:LEV {}', value)

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
                ran = to_float(self.current_range)  # Casting handling Quantity
                res = CURRENT_RESOLUTION[ran]
                if ran != 200e-3:
                    ran *= 1.2
                else:
                    ran = 220e-3
                return FloatLimitsValidator(-ran, ran, res, 'A')
            else:
                return FloatLimitsValidator(1e-3, 0.2, 1e-3, 'A')
