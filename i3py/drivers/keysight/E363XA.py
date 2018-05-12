# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Driver for the keysight E3633A and E3634A DC power source.

"""
from i3py.core import (FloatLimitsValidator, I3pyError, channel, customize,
                       limit, set_feat, subsystem)
from i3py.core.actions import Action
from i3py.core.features import Alias, Bool, Feature, conditional
from i3py.core.unit import to_float, to_quantity

from ..base.dc_sources import (DCPowerSourceWithMeasure,
                               DCSourceTriggerSubsystem,
                               DCSourceProtectionSubsystem)
from ..common.ieee488 import (IEEEInternalOperations,
                              IEEEOptionsIdentification, IEEEPowerOn,
                              IEEEStatusReporting, IEEEStoredSettings,
                              IEEESynchronisation, IEEETrigger)
from ..common.scpi.error_reading import SCPIErrorReading
from ..common.scpi.rs232 import SCPIRS232


class KeysightE363xA(DCPowerSourceWithMeasure, IEEEInternalOperations,
                     IEEEStatusReporting, IEEEOptionsIdentification,
                     IEEEStoredSettings, IEEETrigger, IEEESynchronisation,
                     IEEEPowerOn, SCPIErrorReading, SCPIRS232):
    """Driver for the Keysight E3631A DC power source.

    XXX proper format for IDN

    """
    __version__ = '0.1.0'

    PROTOCOLS = {'GPIB': [{'resource_class': 'INSTR'}],
                 'ASRL': [{'resource_class': 'INSTR'}]
                 }

    DEFAULTS = {'COMMON': {'write_termination': '\n',
                           'read_termination': '\n'}}

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

        o.enabled = set_feat(getter='OUTP?', setter='OUTP {:d}')

        o.voltage = set_feat(
            getter=conditional(('"VOLT?" if driver.trigger.mode != "enabled"'
                                ' else "VOLT:TRIG?"'), default=True),
            setter=conditional(('"VOLT {}" if driver.trigger.mode != "enabled"'
                                ' else "VOLT:TRIG {}"'), default=True),
            limits='voltage')

        o.voltage_range = set_feat(getter='VOLT:RANGE?',
                                   setter='VOLT:RANGE {}')

        o.current = set_feat(
            getter=conditional(('"CURR?" if driver.trigger.mode != "enabled"'
                                ' else "CURR:TRIG?"'), default=True),
            setter=conditional(('"CURR {}" if driver.trigger.mode != "enabled"'
                                ' else "CURR:TRIG {}"'), default=True),
            limits='current')

        o.current_range = set_feat(getter='CURR:RANGE?',
                                   setter='CURR:RANGE {}')

        @o
        @Action(values={'quantity': ("voltage", "current")})
        def measure(self, quantity, **kwargs):
            """Measure the output voltage/current.

            Parameters
            ----------
            quantity : unicode, {'voltage', 'current'}
                Quantity to measure.

            **kwargs :
                This instrument recognize no optional parameters.

            Returns
            -------
            value : float or pint.Quantity
                Measured value. If units are supported the value is a Quantity
                object.

            """
            cmd = 'MEAS:' + ('VOLT' if quantity != 'current' else 'CURR')
            value = float(self.parent.visa_resource.query(cmd))
            value = to_quantity(value, 'V' if quantity != 'current' else 'A')

            return value

        @o
        @Action(unit=(None, (None, 'V', 'A')),
                limits={'voltage': 'voltage', 'current': 'current'})
        def apply(self, voltage, current):
            """Set both the voltage and current limit.

            """
            with self.lock:
                self.parent.visa_resource.write(f'APPLY {voltage}, {current}')
                res, msg = self.parent.read_error()
            if res != 0:
                err = 'Failed to apply {}V, {}A to output {} :\n{}'
                raise I3pyError(err.format(voltage, current, self.id, msg))

        o.trigger = subsystem(DCSourceTriggerSubsystem)

        with o.trigger as t:

            # HINT this is a soft feature !!!
            t.mode = set_feat(getter=True, setter=True,
                              values=('disabled', 'enabled'))

            t.source = set_feat('TRIG:SOUR?', 'TRIG:SOUR {}',
                                mapping={'immediate': 'IMM', 'bus': 'BUS'})

            t.delay = set_feat('TRIG:DEL?', 'TRIG:DEL {}',
                               limits=(1, 3600, 1))

            @o
            @Action()
            def arm(self):
                """Prepare the channel to receive a trigger.

                If the trigger mode is immediate the update occurs as soon as
                the command is processed.

                """
                with self.lock:
                    self.write('INIT')
                    res, msg = self.root.read_error()
                if res:
                    err = 'Failed to arm the trigger for output {}:\n{}'
                    raise I3pyError(err.format(self.id, msg))

            # HINT mode is a "soft" feature meaning it has no reality for the
            # the instrument. As a consequence having a default value is enough
            # the caching does the rest for us.
            @t
            @customize('mode', 'get')
            def _get_mode(feat, driver):
                return 'disabled'

            @t
            @customize('mode', 'set')
            def _set_mode(feat, driver, value):
                vrsc = driver.root.visa_resource
                vrsc.write(f'VOLT:TRIG {driver.parent.voltage}')
                vrsc.write(f'CURR:TRIG {driver.parent.current}')
                res, msg = self.root.read_error()
                if res:
                    err = ('Failed to set the triggered values for voltage '
                           'and current {}:\n{}')
                    raise I3pyError(err.format(self.id, msg))


VOLTAGE_RANGES = {'P6V': 6, 'P25V': 25, 'N25V': -25}

CURRENT_RANGES = {'P6V': 5, 'P25V': 1, 'N25V': 1}


class KeysightE3631A(KeysightE363xA):
    """Driver for the Keysight E3631A DC power source.

    """
    #: In this model, outputs are always enabled together.
    outputs_enabled = Bool('OUTP?', 'OUTP {:d}',
                           aliases={True: ['On', 'ON', 'On'],
                                    False: ['Off', 'OFF', 'off']})

    #: Whether to couple together the output triggers, causing a trigger
    #: received on one to update the other values.
    coupled_triggers = Feature(getter=True, setter=True,
                               checks=(None, ('value is False or '
                                              'not driver.outputs_tracking'))
                               )

    #: Activate tracking between the P25V and the N25V output. In tracking
    #: one have P25V.voltage = - N25V
    outputs_tracking = Bool('OUTP:TRAC?',
                            'OUTP:TRAC {}',
                            aliases={True: ['On', 'ON', 'On'],
                                     False: ['Off', 'OFF', 'off']},
                            checks=(None,
                                    ('value is False or'
                                     'driver.coupled_triggers is None or '
                                     '1 not in driver.coupled_triggers or '
                                     '2 not in driver.coupled_triggers')))

    output = channel((0, 1, 2),
                     aliases={'P6V': 0, 'P25V': 1, 'N25V': 2})

    with output as o:

        o.enabled = Alias('.outputs_enabled')  # should this be settable ?

        o.voltage_range = set_feat(getter=True)

        o.current_range = set_feat(getter=True)

        @o
        @Action(lock=True, values={'quantity': ('voltage', 'current')})
        def measure(self, quantity, **kwargs):
            """Measure the output voltage/current.

            Parameters
            ----------
            quantity : unicode, {'voltage', 'current'}
                Quantity to measure.

            **kwargs :
                This instrument recognize no optional parameters.

            Returns
            -------
            value : float or pint.Quantity
                Measured value. If units are supported the value is a Quantity
                object.

            """
            self.parent.write('INSTR:SELECT %s' % self.id)
            super().measure(quantity, **kwargs)

        @o
        @Action(lock=True)
        def apply(self, voltage, current):
            """Set both the voltage and current limit.

            """
            self.parent.write('INSTR:SELECT %s' % self.id)
            super().apply(voltage, current)

        @o
        @Action()
        def read_output_status(self):
            """Read the status of the output.

            Returns
            -------
            status : unicode, {'disabled',
                               'enabled:constant-voltage',
                               'enabled:constant-current',
                               'tripped:over-voltage',
                               'tripped:over-current',
                               'unregulated'}

            """
            if not self.enabled:
                return 'disabled'
            status = int(self.parent.visa_resource(
                f'STAT:QUES:INST:ISUM{self.id + 1}?'))
            if status & 1:
                return 'enabled:constant-voltage'
            if status & 2:
                return 'enabled:constant-current'
            return 'unregulated'

        o.trigger = subsystem(DCSourceTriggerSubsystem)

        with o.trigger as t:

            @o
            @Action(lock=True)
            def arm(self):
                """Prepare the channel to receive a trigger.

                If the trigger mode is immediate the update occurs as soon as
                the command is processed.

                """
                self.root.visa_resource.write(f'INSTR:NSEL {self.id + 1}')
                super().arm()

        @o
        def default_get_feature(self, feat, cmd, *args, **kwargs):
            """Always select the channel before getting.

            """
            cmd = f'INSTR:NSEL {self.id + 1};' + cmd
            return super().default_get_feature(feat, cmd, *args, **kwargs)

        @o
        def default_set_feature(self, feat, cmd, *args, **kwargs):
            """Always select the channel before getting.

            """
            cmd = f'INSTR:NSEL {self.id + 1};' + cmd
            return super().default_set_feature(feat, cmd, *args, **kwargs)

        @o
        @customize('voltage', 'post_set', ('append',))
        def _post_setattr_voltage(self, feat, value, i_value, state=None):
            """Make sure that in tracking mode the voltage cache is correct.

            """
            if self.id != 0:
                del self.parent.output[1].voltage
                del self.parent.output[2].voltage

        @o
        @customize('voltage_range', 'get')
        def _get_voltage_range(self, feat):
            """Get the voltage range.

            """
            return VOLTAGE_RANGES[self.id]

        @o
        @customize('current_range', 'get')
        def _get_current_range(self, feat):
            """Get the current range.

            """
            return CURRENT_RANGES[self.id]

        @o
        @limit('voltage')
        def _limits_voltage(self):
            """Build the voltage limits matching the output.

            """
            if self.id == 'P6V':
                return FloatLimitsValidator(0, 6.18, 1e-3, unit='V')
            elif self.id == 'P25V':
                return FloatLimitsValidator(0, 25.75, 1e-2, unit='V')
            else:
                return FloatLimitsValidator(-25.75, 0, 1e-2, unit='V')

        @o
        @limit('current')
        def _limits_current(self):
            """Build the current limits matching the output.

            """
            if self.id == 'P6V':
                return FloatLimitsValidator(0, 5.15, 1e-3, unit='A')
            elif self.id == 'P25V':
                return FloatLimitsValidator(0, 1.03, 1e-3, unit='A')
            else:
                return FloatLimitsValidator(0, 1.03, 1e-3, unit='A')


class KeysightE3633A(KeysightE363xA):
    """Driver for the Keysight E3633A DC power source.

    """
    __version__ = '0.1.0'

    output = channel((0,))

    with output as o:

        o.voltage_range = set_feat(values=(8, 20))

        o.current_range = set_feat(values=(20, 10))

        o.over_voltage_protection = subsystem(DCSourceProtectionSubsystem)

        with o.over_voltage_protection as ovp:

            ovp.enabled = set_feat(getter='VOLT:PROC:STAT?',
                                   setter='VOLT:PROC:STAT {:d}')

            ovp.high_level = set_feat(getter='VOLT:PROT:LEV?',
                                      setter='VOLT:PROT:LEV {}')

            ovp.low_level = set_feat(getter=True, setter=True)

            @ovp
            @Action()
            def read_status(self) -> str:
                """Read the status of the voltage protection

                """
                return ('tripped'
                        if self.root.visa_resource.query('VOLT:PROT:TRIP?')
                        else 'working')

            @ovp
            @Action()
            def clear(self) -> None:
                """Clear the voltage protection status.

                """
                root = self.root
                root.visa_resource.write('VOLT:PROT:CLEAR')
                res, msg = root.read_error()
                if res:
                    raise I3pyError(
                        f'Failed to clear voltage protection: {msg}')

            @ovp
            @customize('low_level', 'get')
            def _get_low_level(feat, driver):
                return - driver.high_level

            @ovp
            @customize('low_level', 'get')
            def _set_low_level(feat, driver, value):
                driver.high_level = - value

        o.over_current_protection = subsystem(DCSourceProtectionSubsystem)

        with o.over_current_protection as ocp:

            ovp.enabled = set_feat(getter='CURR:PROC:STAT?',
                                   setter='CURR:PROC:STAT {:d}')

            ovp.high_level = set_feat(getter='CURR:PROT:LEV?',
                                      setter='CURR:PROT:LEV {}')

            ovp.low_level = set_feat(getter=True, setter=True)

            @ovp
            @Action()
            def read_status(self) -> str:
                """Read the status of the voltage protection

                """
                return ('tripped'
                        if self.root.visa_resource.query('CURR:PROT:TRIP?')
                        else 'working')

            @ovp
            @Action()
            def clear(self) -> None:
                """Clear the voltage protection status.

                """
                root = self.root
                root.visa_resource.write('CURR:PROT:CLEAR')
                res, msg = root.read_error()
                if res:
                    raise I3pyError(
                        f'Failed to clear voltage protection: {msg}')

            @ovp
            @customize('low_level', 'get')
            def _get_low_level(feat, driver):
                return - driver.high_level

            @ovp
            @customize('low_level', 'get')
            def _set_low_level(feat, driver, value):
                driver.high_level = - value

        @o
        @Action()
        def read_output_status(self):
            """Read the status of the output.

            Returns
            -------
            status : unicode, {'disabled',
                               'enabled:constant-voltage',
                               'enabled:constant-current',
                               'tripped:over-voltage',
                               'tripped:over-current',
                               'unregulated'}

            """
            status = self.parent.visa_resource.query('STAT:QUES:COND?')
            if status == '0':
                return 'disabled' if not self.enabled else 'unregulated'
            elif status == '1':
                return 'enabled:constant-voltage'
            elif status == '2':
                return 'enabled:constant-current'
            else:
                if self.over_voltage_protection.read_status() == 'tripped':
                    return 'tripped:over-voltage'
                else:
                    return 'tripped:over-current'

        @o
        @limit('voltage')
        def _limits_voltage(self):
            """Build the voltage limits.

            """
            if to_float(self.voltage_range) == 8:
                return FloatLimitsValidator(0, 8.24, 1e-3, unit='V')
            else:
                return FloatLimitsValidator(0, 20.6, 1e-2, unit='V')

        @o
        @limit('current')
        def _limits_current(self):
            """Build the current limits.

            """
            if to_float(self.current_range) == 20:
                return FloatLimitsValidator(0, 20.60, 1e-3, unit='A')
            else:
                return FloatLimitsValidator(0, 10.3, 1e-3, unit='A')


class KeysightE3634A(KeysightE3633A):
    """Driver for the Keysight E3634A DC power source.

    """
    __version__ = '0.1.0'

    output = channel((0,))

    with output as o:

        o.voltage_range = set_feat(values=(25, 50))

        o.current_range = set_feat(values=(7, 4))

        @o
        @limit('voltage')
        def _limits_voltage(self):
            """Build the voltage limits based on the range.

            """
            if to_float(self.voltage_range) == 25:
                return FloatLimitsValidator(0, 25.75, 1e-3, unit='V')
            else:
                return FloatLimitsValidator(0, 51.5, 1e-3, unit='V')

        @o
        @limit('current')
        def _limits_current(self):
            """Build the current limits based on the range.

            """
            if to_float(self.current_range) == 7:
                return FloatLimitsValidator(0, 7.21, 1e-3, unit='A')
            else:
                return FloatLimitsValidator(0, 4.12, 1e-3, unit='A')
