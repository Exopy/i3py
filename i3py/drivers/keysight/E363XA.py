# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Driver for the Keysight E3631A, E3633A and E3634A DC power source.

"""
from i3py.core import (FloatLimitsValidator, I3pyError, channel, customize,
                       limit, set_feat, subsystem)
from i3py.core.actions import Action
from i3py.core.features import Alias, Bool, Feature, conditional
from i3py.core.unit import to_float, to_quantity

from ..base.dc_sources import (DCPowerSourceWithMeasure,
                               DCSourceProtectionSubsystem,
                               DCSourceTriggerSubsystem)
from ..common.ieee488 import (IEEEInternalOperations, IEEEPowerOn,
                              IEEEStatusReporting, IEEEStoredSettings,
                              IEEESynchronisation, IEEETrigger)
from ..common.scpi.error_reading import SCPIErrorReading


class E363xA(DCPowerSourceWithMeasure, IEEEInternalOperations,
             IEEEStatusReporting, IEEEStoredSettings, IEEETrigger,
             IEEESynchronisation, IEEEPowerOn, SCPIErrorReading):
    """Driver for the Keysight E3631A DC power source.

    """
    __version__ = '0.1.0'

    PROTOCOLS = {'GPIB': [{'resource_class': 'INSTR'}],
                 'ASRL': [{'resource_class': 'INSTR'}]
                 }

    DEFAULTS = {'COMMON': {'write_termination': '\n',
                           'read_termination': '\n'}}

    outputs = channel((0,))

    with outputs as o:

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
        @Action(values={'quantity': ("voltage", "current")},
                lock=True)
        def measure(self, quantity, **kwargs):
            """Measure the output voltage/current.

            Parameters
            ----------
            quantity : str, {'voltage', 'current'}
                Quantity to measure.

            **kwargs :
                This instrument recognize no optional parameters.

            Returns
            -------
            value : float or pint.Quantity
                Measured value. If units are supported the value is a Quantity
                object.

            """
            cmd = 'MEAS:' + ('VOLT?' if quantity != 'current' else 'CURR?')
            value = float(self.parent.visa_resource.query(cmd))
            value = to_quantity(value, 'V' if quantity != 'current' else 'A')

            return value

        @o
        @Action(unit=(None, (None, 'V', 'A')),
                limits={'voltage': 'voltage', 'current': 'current'},
                discard=('voltage', 'current'),
                lock=True)
        def apply(self, voltage, current):
            """Set both the voltage and current limit.

            """
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

            t.source = set_feat(getter='TRIG:SOUR?', setter='TRIG:SOUR {}',
                                mapping={'immediate': 'IMM', 'bus': 'BUS'})

            t.delay = set_feat(getter='TRIG:DEL?', setter='TRIG:DEL {}',
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
                res, msg = driver.root.read_error()
                if res:
                    err = ('Failed to set the triggered values for voltage '
                           'and current {}:\n{}')
                    raise I3pyError(err.format(driver.id, msg))


VOLTAGE_RANGES = {0: 6, 1: 25, 2: -25}

CURRENT_RANGES = {0: 5, 1: 1, 2: 1}


class E3631A(E363xA):
    """Driver for the Keysight E3631A DC power source.

    """
    __version__ = '0.1.0'

    #: In this model, outputs are always enabled together.
    outputs_enabled = Bool('OUTP?', 'OUTP {}',
                           mapping={True: '1', False: '0'},
                           aliases={True: ['On', 'ON', 'On'],
                                    False: ['Off', 'OFF', 'off']})

    #: Whether to couple together the output triggers, causing a trigger
    #: received on one to update the other values.
    #: The value is a tuple containing the indexes of the outputs for which the
    #: triggers are coupled.
    coupled_triggers = Feature('INST:COUP?', 'INST:COUP {}',
                               checks=(None, ('value is False or '
                                              'not driver.outputs_tracking'))
                               )

    @customize('coupled_triggers', 'post_get', ('append',))
    def _post_get_coupled_triggers(feat, driver, value):
        """Get the currently coupled triggers.

        """
        if value == 'NONE':
            return ()
        elif value == 'ALL':
            return (0, 1, 2)
        else:
            return tuple(i for i, id in enumerate(('P6V', 'P25V', 'N25V'))
                         if id in value)

    @customize('coupled_triggers', 'pre_set', ('append',))
    def _pre_set_coupled_triggers(feat, driver, value):
        """Properly format the value for setting the coupled triggers.

        """
        aliases = driver.outputs.aliases
        names = []
        if len(value) != len(set(value)):
            raise ValueError('Impossible to couple to identical outputs '
                             f'({value})')
        for index in value:
            if index not in aliases:
                raise ValueError(f'Invalid output index: {index}')
            names.append(aliases[index])

        if not names:
            return 'NONE'
        elif len(names) == 3:
            return 'ALL'
        else:
            return ','.join(names)

    #: Activate tracking between the P25V and the N25V output. In tracking
    #: one have P25V.voltage = - N25V
    outputs_tracking = Bool('OUTP:TRAC?',
                            'OUTP:TRAC {}',
                            mapping={True: '1', False: '0'},
                            aliases={True: ['On', 'ON', 'On'],
                                     False: ['Off', 'OFF', 'off']},
                            checks=(None,
                                    ('value is False or '
                                     'driver.coupled_triggers is None or '
                                     '1 not in driver.coupled_triggers or '
                                     '2 not in driver.coupled_triggers')))

    outputs = channel((0, 1, 2),
                      aliases={0: 'P6V', 1: 'P25V', 2: 'N25V'})

    with outputs as o:

        o.enabled = Alias('.outputs_enabled')  # should this be settable ?

        o.voltage_range = set_feat(getter=True)

        o.current_range = set_feat(getter=True)

        @o
        @Action(lock=True, values={'quantity': ('voltage', 'current')})
        def measure(self, quantity, **kwargs):
            """Measure the output voltage/current.

            Parameters
            ----------
            quantity : str, {'voltage', 'current'}
                Quantity to measure.

            **kwargs :
                This instrument recognize no optional parameters.

            Returns
            -------
            value : float or pint.Quantity
                Measured value. If units are supported the value is a Quantity
                object.

            """
            self.parent.visa_resource.write(f'INST:NSEL {self.id + 1}')
            return super(E3631A.outputs, self).measure(quantity, **kwargs)

        @o
        @Action(unit=(None, (None, 'V', 'A')),
                limits={'voltage': 'voltage', 'current': 'current'},
                discard=('voltage', 'current'),
                lock=True)
        def apply(self, voltage, current):
            """Set both the voltage and current limit.

            """
            self.parent.visa_resource.write(f'INST:NSEL {self.id + 1}')
            super(E3631A.outputs, self).apply(voltage, current)

        @o
        @Action()
        def read_output_status(self):
            """Read the status of the output.

            Returns
            -------
            status : str, {'disabled',
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
                super(E3631A.outputs.trigger).arm()

        @o
        def default_get_feature(self, feat, cmd, *args, **kwargs):
            """Always select the channel before getting.

            """
            self.root.visa_resource.write(f'INST:NSEL {self.id + 1}')
            return super(E3631A.outputs,
                         self).default_get_feature(feat, cmd, *args, **kwargs)

        @o
        def default_set_feature(self, feat, cmd, *args, **kwargs):
            """Always select the channel before getting.

            """
            self.root.visa_resource.write(f'INST:NSEL {self.id + 1}')
            return super(E3631A.outputs,
                         self).default_set_feature(feat, cmd, *args, **kwargs)

        @o
        @customize('voltage', 'post_set', ('append',))
        def _post_setattr_voltage(feat, driver, value, i_value, response):
            """Make sure that in tracking mode the voltage cache is correct.

            """
            if driver.id != 0:
                del driver.parent.outputs[1].voltage
                del driver.parent.outputs[2].voltage

        @o
        @customize('voltage_range', 'get')
        def _get_voltage_range(feat, driver):
            """Get the voltage range.

            """
            return VOLTAGE_RANGES[driver.id]

        @o
        @customize('current_range', 'get')
        def _get_current_range(feat, driver):
            """Get the current range.

            """
            return CURRENT_RANGES[driver.id]

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


class E3633A(E363xA):
    """Driver for the Keysight E3633A DC power source.

    """
    __version__ = '0.1.0'

    outputs = channel((0,))

    with outputs as o:

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
            @customize('low_level', 'set')
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
            @customize('low_level', 'set')
            def _set_low_level(feat, driver, value):
                driver.high_level = - value

        @o
        @Action()
        def read_output_status(self):
            """Read the status of the output.

            Returns
            -------
            status : str, {'disabled',
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


class E3634A(E3633A):
    """Driver for the Keysight E3634A DC power source.

    """
    __version__ = '0.1.0'

    outputs = channel((0,))

    with outputs as o:

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
