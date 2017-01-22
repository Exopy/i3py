# -*- coding: utf-8 -*-
"""
    lantz_drivers.keysight.model_E363XA
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Driver for the keysight E3633A and E3634A DC power source.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from lantz_core import set_feat, channel, subsystem, Action
from lantz_core.errors import LantzError
from lantz_core.limits import FloatLimitsValidator
from lantz_core.unit import to_float, to_quantity
from lantz_core.features import Feature, Bool, Alias, conditional
from lantz_core.features.util import append

from ..base.dc_sources import (DCPowerSourceWithMeasure,
                               DCSourceTriggerSubsystem)
from ..common.ieee488 import (IEEEInternalOperations, IEEEStatusReporting,
                              IEEEOperationComplete, IEEEOptionsIdentification,
                              IEEEStoredSettings, IEEETrigger,
                              IEEESynchronisation, IEEEPowerOn)
from ..common.scpi.error_reading import SCPIErrorReading
from ..common.scpi.rs232 import SCPIRS232


class _KeysightE363XA(DCPowerSourceWithMeasure, IEEEInternalOperations,
                      IEEEStatusReporting, IEEEOperationComplete,
                      IEEEOptionsIdentification, IEEEStoredSettings,
                      IEEETrigger, IEEESynchronisation, IEEEPowerOn,
                      SCPIErrorReading, SCPIRS232):
    """Driver for the Keysight E3631A DC power source.

    """
    PROTOCOLS = {'GPIB': 'INSTR', 'ASRL': 'INSTR'}

    DEFAULTS = {'COMMON': {'write_termination': '\n',
                           'read_termination': '\n'}}

    output = channel()

    with output as o:

        o.enabled = set_feat(getter='OUTP?', setter='OUTP {}',
                             aliases={True: ['On', 'ON', 'On'],
                                      False: ['Off', 'OFF', 'off']})

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
        @Action(checks={'quantity': 'value in ("voltage", "current")'})
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
            cmd = 'MEAS:'
            cmd += 'VOLT' if quantity != 'current' else 'CURR'
            value = float(self.parent.query(cmd))
            value = to_quantity(value, 'V' if quantity != 'current' else 'A')

            return value

        @o
        @Action(unit=(None, (None, 'V', 'A')),
                limits={'voltage': 'voltage', 'current': 'current'})
        def apply(self, voltage, current):
            """Set both the voltage and current limit.

            """
            with self.lock:
                self.parent.write('APPLY {}, {}'.format(self.id, voltage,
                                                        current))
                res, msg = self.parent.read_error()
            if res:
                err = 'Failed to apply {}V, {}A to output {} :\n{}'
                raise LantzError(err.format(voltage, current, self.id, msg))
# XXXX
        @o
        @Action()
        def read_output_status(self):
            """
            """
            pass

        o.trigger = subsystem(DCSourceTriggerSubsystem)

        with o.trigger as t:

            #:
            t.mode = set_feat(getter=True, setter=True)

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
                    res, msg = self.parent.parent.read_error()
                if res:
                    err = 'Failed to arm the trigger for output {}:\n{}'
                    raise LantzError(err.format(self.id, msg))

            # Actually the caching do the rest for us.
            @t
            def _get_mode(self, feat):
                return 'disabled'

            @t
            def _set_mode(self, feat, value):
                pass


VOLTAGE_RANGES = {'P6V': 6, 'P25V': 25, 'N25V': -25}

CURRENT_RANGES = {'P6V': 5, 'P25V': 1, 'N25V': 1}


class KeysightE3631A(_KeysightE363XA):
    """Driver for the Keysight E3631A DC power source.

    """
    PROTOCOLS = {'GPIB': 'INSTR', 'ASRL': 'INSTR'}

    DEFAULTS = {'COMMON': {'write_termination': '\n',
                           'read_termination': '\n'}}

    #: In this model, outputs are always enabled together.
    outputs_enabled = Bool('OUTP?', 'OUTP {}',
                           aliases={True: ['On', 'ON', 'On'],
                                    False: ['Off', 'OFF', 'off']})

    #: Whether to couple together teh output triggers, causing a trigger
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

    output = channel(('P6V', 'P25V', 'N25V'),
                     aliases={0: 'P6V', 1: 'P25V', 2: 'N25V'})

    with output as o:

        o.enabled = Alias('.outputs_enabled')  #: should this be settable ?

        o.voltage_range = set_feat(getter=True)

        o.current_range = set_feat(getter=True)

        @o
        @Action()
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
            with self.lock:
                self.parent.write('INSTR:SELECT %s' % self.id)
                super(KeysightE3631A.output, self).measure(quantity, **kwargs)

        @o
        @Action()
        def apply(self, voltage, current):
            """Set both the voltage and current limit.

            """
            with self.lock:
                self.parent.write('INSTR:SELECT %s' % self.id)
                super(KeysightE3631A.output, self).apply(voltage, current)
# XXXX
        @o
        @Action()
        def read_output_status(self):
            """Read the status of the output.

            Returns
            -------
            status : unicode, {'disabled',
                               'constant voltage', 'constant voltage',
                               'tripped, voltage', 'tripped, current',
                               'unregulated'}

            """
            pass

        o.trigger = subsystem(DCSourceTriggerSubsystem)

        with o.trigger as t:

            @o
            @Action()
            def arm(self):
                """Prepare the channel to receive a trigger.

                If the trigger mode is immediate the update occurs as soon as
                the command is processed.

                """
                with self.lock:
                    self.parent.parent.write('INSTR:SELECT %s' % self.id)
                    super(KeysightE3631A.output.trigger, self).arm()

        @o
        def default_get_feature(self, feat, cmd, *args, **kwargs):
            """Always select the channel before getting.

            """
            cmd = 'INSTR:SELECT {ch_id};' + cmd
            kwargs['ch_id'] = self.id
            return super(type(self), self).default_get_feature(feat, cmd,
                                                               *args, **kwargs)

        @o
        def default_set_feature(self, feat, cmd, *args, **kwargs):
            """Always select the channel before getting.

            """
            cmd = 'INSTR:SELECT {ch_id};' + cmd
            kwargs['ch_id'] = self.id
            return super(type(self), self).default_set_feature(feat, cmd,
                                                               *args, **kwargs)

        @o
        @append
        def _post_setattr_voltage(self, feat, value, i_value, state=None):
            """Make sure that in tracking mode teh voltage cache is correct.

            """
            if self.id != 'P6V':
                self.parent.output['P25V'].clear_cache(features=('voltage',))
                self.parent.output['N25V'].clear_cache(features=('voltage',))

        @o
        def _get_voltage_range(self, feat):
            """Get the voltage range.

            """
            return VOLTAGE_RANGES[self.id]

        @o
        def _get_current_range(self, feat):
            """Get the current range.

            """
            return CURRENT_RANGES[self.id]

        @o
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
        def _limits_current(self):
            """Build the current limits matching the output.

            """
            if self.id == 'P6V':
                return FloatLimitsValidator(0, 5.15, 1e-3, unit='A')
            elif self.id == 'P25V':
                return FloatLimitsValidator(0, 1.03, 1e-3, unit='A')
            else:
                return FloatLimitsValidator(0, 1.03, 1e-3, unit='A')


class KeysightE3633A(_KeysightE363XA):
    """Driver for the Keysight E3633A DC power source.

    """
    output = channel()

    with output as o:

        o.voltage_range = set_feat(values=(8, 20))

        o.current_range = set_feat(values=(20, 10))

        @o
        def _limits_voltage(self):
            """Build the voltage limits.

            """
            if to_float(self.voltage_range) == 8:
                return FloatLimitsValidator(0, 8.24, 1e-3, unit='V')
            else:
                return FloatLimitsValidator(0, 20.6, 1e-2, unit='V')

        @o
        def _limits_current(self):
            """Build the current limits.

            """
            if to_float(self.current_range) == 20:
                return FloatLimitsValidator(0, 20.60, 1e-3, unit='A')
            else:
                return FloatLimitsValidator(0, 10.3, 1e-3, unit='A')


class KeysightE3634A(_KeysightE363XA):
    """Driver for the Keysight E3634A DC power source.

    """
    output = channel()

    with output as o:

        o.voltage_range = set_feat(values=(25, 50))

        o.current_range = set_feat(values=(7, 4))

        @o
        def _limits_voltage(self):
            """Build the voltage limits based on the range.

            """
            if to_float(self.voltage_range) == 25:
                return FloatLimitsValidator(0, 25.75, 1e-3, unit='V')
            else:
                return FloatLimitsValidator(0, 51.5, 1e-3, unit='V')

        @o
        def _limits_current(self):
            """Build the current limits based on the range.

            """
            if to_float(self.current_range) == 7:
                return FloatLimitsValidator(0, 7.21, 1e-3, unit='A')
            else:
                return FloatLimitsValidator(0, 4.12, 1e-3, unit='A')
