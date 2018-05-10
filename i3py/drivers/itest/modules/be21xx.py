# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Package for the Itest BE21xx voltage source card.

"""
from typing import Callable, Optional

from i3py.core import (FloatLimitsValidator, channel, customize, set_feat,
                       subsystem, limit)
from i3py.core.actions import Action
from i3py.core.features import Float, Str, Bool, constant
from i3py.core.job import InstrJob
from i3py.core.unit import FLOAT_QUANTITY, to_float
from stringparser import Parser

from ...base.dc_sources import (DCPowerSourceWithMeasure,
                                DCSourceTriggerSubsystem)
from ...base.identity import Identity
from .common import BiltModule


class BE21xx(BiltModule, DCPowerSourceWithMeasure):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'

    #: Identity support (we do not use IEEEIdentity because we are not on the
    #: root level).
    identity = subsystem(Identity)

    with identity as i:

        #: Format string specifying the format of the IDN query answer and
        #: allowing to extract the following information:
        #: - manufacturer: name of the instrument manufacturer
        #: - model: name of the instrument model
        #: - serial: serial number of the instrument
        #: - firmware: firmware revision
        #: ex {manufacturer},<{model}>,SN{serial}, Firmware revision {firmware}
        i.IEEE_IDN_FORMAT = ('{_:d},"{manufacturer:s} {model:s}BB/{_:s}'
                             '/SN{serial:s}\\{_:s} LC{_:s} VL{firmware:s}'
                             '\\{_:d}"')

        i.manufacturer = set_feat(getter='*IDN?')
        i.model = set_feat(getter='*IDN?')
        i.serial = set_feat(getter='*IDN?')
        i.firmware = set_feat(getter='*IDN?')

        def _post_getter(feat, driver, value):
            """Get the identity info from the *IDN?.

            """
            infos = Parser(driver.IEEE_IDN_FORMAT)(value)
            driver._cache.update(infos)
            return infos.get(feat.name, '')

        for f in ('manufacturer', 'model', 'serial', 'firmware'):
            setattr(i, '_post_get_' + f,
                    customize(f, 'post_get')(_post_getter))

    #: DC outputs
    output = channel((0,))

    with output as o:

        o.enabled = set_feat(getter='OUTP?', setter='OUTP {}',
                             mapping={False: '0', True: '1'},
                             checks=(None,
                                     'driver.read_output_status() == '
                                     '"constant-voltage"')
                             )

        o.voltage = set_feat(getter='VOLT?', setter='VOLT {:E}',
                             limits='voltage')

        o.voltage_range = set_feat(getter='VOLT:RANG?', setter='VOLT:RANG {}',
                                   values=(1.2, 12), extract='{},{_}',
                                   checks=(None, 'not driver.enabled'),
                                   discard={'features': ('voltage',),
                                            'limits': ('voltage',)})

        #: Specify stricter voltage limitations than the ones linked to the
        #: range.
        o.voltage_saturation = subsystem()
        with o.voltage_saturation as vs:

            #: Is the low voltage limit enabled. If this conflict with the
            #: current voltage, the voltage will clipped to th smallest allowed
            #: value.
            vs.low_enabled = Bool('VOLT:SAT:NEG?', 'VOLT:SAT:NEG {}',
                                  discard={'features': ('.voltage',),
                                           'limits': ('.voltage',)})

            @vs
            @customize('low_enabled', 'post_get', ('prepend',))
            def _convert_low_answer(feat, driver, value):
                return not value == 'MIN'

            @vs
            @customize('low_enabled', 'pre_set', ('append',))
            def _prepare_low_answer(feat, driver, value):
                if value:
                    return driver.low
                else:
                    return 'MIN'

            #: Is the high voltage limit enabled. If this conflict with the
            #: current voltage, the voltage will clipped to th largest allowed
            #: value.
            vs.high_enabled = Bool('VOLT:SAT:POS?', 'VOLT:SAT:POS {}',
                                   discard={'features': ('.voltage',),
                                            'limits': ('.voltage',)})

            @vs
            @customize('high_enabled', 'post_get', ('prepend',))
            def _convert_high_answer(feat, driver, value):
                return not value == 'MAX'

            @vs
            @customize('high_enabled', 'pre_set', ('append',))
            def _prepare_high_answer(feat, driver, value):
                if value:
                    return driver.high
                else:
                    return 'MAX'

            #: Lowest allowed voltage. If this conflict with the current
            #: voltage, the voltage will clipped to th smallest allowed
            #: value.
            vs.low = Float('VOLT:SAT:NEG?', 'VOLT:SAT:NEG {}', unit='V',
                           limits=(-12, 0),
                           discard={'features': ('.voltage',),
                                    'limits': ('.voltage',)})

            #: Highest allowed voltage. If this conflict with the current
            #: voltage, the voltage will clipped to th smallest allowed
            #: value.
            vs.high = Float('VOLT:SAT:POS?', 'VOLT:SAT:POS {}', unit='V',
                            limits=(0, 12),
                            discard={'features': ('.voltage',),
                                     'limits': ('.voltage',)})

            @vs
            @customize('low', 'post_get', ('prepend',))
            def _convert_min(feat, driver, value):
                if value == 'MIN':
                    value = '-12'
                return value

            @vs
            @customize('high', 'post_get', ('prepend',))
            def _convert_max(feat, driver, value):
                if value == 'MAX':
                    value = '12'
                return value

        o.current = set_feat(getter=constant(0.2))

        o.current_range = set_feat(getter=constant(0.2))

        #: Subsystem handling triggering and reaction to triggering.
        o.trigger = subsystem(DCSourceTriggerSubsystem)
        with o.trigger as tr:
            #: Type of response to triggering :
            #: - disabled : immediate update of voltage every time the voltage
            #:   feature is updated.
            #: - slope : update after receiving a trigger based on the slope
            #:   value.
            #: - stair : update after receiving a trigger using step_amplitude
            #:   and step_width.
            #: - step : increment by one step_amplitude till target value for
            #:   each triggering.
            #: - auto : update after receiving a trigger by steps but
            #:   determining when to move to next step based on voltage
            #:   sensing.
            tr.mode = Str('TRIG:IN?', 'TRIG:IN {}',
                          mapping={'disabled': '0', 'slope': '1',
                                   'stair': '2', 'step': '4', 'auto': '5'})

            #: The only valid source for the trigger is software trigger.
            tr.source = Str(constant('software'))

            #: Delay to wait after receiving a trigger event before reacting.
            tr.delay = set_feat(getter='TRIG:IN:DEL?', setter='TRIG:IN:DEL {}',
                                unit='ms', limits=(0, 60000, 1))

            #: Voltage slope to use in slope mode.
            tr.slope = Float('VOLT:SLOP?', 'VOLT:SLOP {}', unit='V/ms',
                             limits=(1.2e-6, 1))

            #: High of each update in stair and step mode.
            tr.step_amplitude = Float('VOLT:ST:AMPL?', 'VOLT:ST:AMPL {}',
                                      unit='V', limits='voltage')

            #: Width of each step in stair mode.
            tr.step_width = Float('VOLT:ST:WID?', 'VOLT:ST:WID {}', unit='ms',
                                  limits=(100, 60000, 1))

            #: Absolute threshold value of the settling tracking comparator.
            tr.ready_amplitude = Float('TRIG:READY:AMPL?',
                                       'TRIG:READY:AMPL {}',
                                       unit='V', limits=(1.2e-6, 1))

            @tr
            @Action(retries=1)
            def fire(self):
                """Send a software trigger.

                """
                msg = self.parent._header_() + 'TRIG:IN:INIT'
                self.root.visa_resource.write(msg)

            @tr
            @Action(retries=1)
            def is_trigger_ready(self) -> bool:
                """Check if the output is within ready_amplitude of the target
                value.

                """
                msg = self.parent._header_() + 'TRIG:READY?'
                return bool(int(self.root.visa_resource.query(msg)))

        #: Status of the output. Save for the first one, they are all related
        #: to dire issues that lead to switching off the output.
        o.OUTPUT_STATES = {0: 'enabled:constant-voltage',
                           5: 'tripped:main-failure',
                           6: 'tripped:system-failure',
                           7: 'tripped:temperature-failure',
                           8: 'unregulated'}

        @o
        @Action(retries=1)
        def read_output_status(self) -> str:
            """Determine the current status of the output.

            """
            if not self.enabled:
                return 'disabled'
            msg = self._header_() + 'LIM:FAIL?'
            answer = int(self.root.visa_resource.query(msg))
            # If a failure occured the whole card switches off.
            if answer != 0:
                for o in self.parent.output:
                    del self.enabled
            return self.OUTPUT_STATES.get(answer, f'unknown({answer})')

        @o
        @Action(retries=1)
        def clear_output_status(self) -> None:
            """Clear the error condition of the output.

            This must be called after a failure before switching the output
            back on

            """
            self.root.visa_resource.write(self._header_() + 'LIM:CLEAR')
            if not self.read_output_status() == 'normal':
                raise RuntimeError('Failed to clear output status.')

        @o
        @Action(retries=1, checks='driver.trigger.mode != "disabled"')
        def read_voltage_status(self) -> str:
            """Progression of the current voltage update.

            This action return meaningful values if we use a triggered setting
            of the output.

            Returns
            -------
            status: {'waiting', 'settled', 'changing'}
                Status of the output voltage.

            """
            msg = self._header_() + 'VOLT:STAT?'
            status = float(self.root.visa_resource.query(msg))
            if status == 1:
                return 'settled'
            elif status == 0:
                return 'waiting'
            else:
                return 'changing'

        @o
        @Action(unit=((None, None, None), 'V'),
                values={'quantity': ('voltage',)}, retries=1)
        def measure(self, quantity, **kwargs) -> FLOAT_QUANTITY:
            """Measure the output voltage.

            """
            msg = self._header_() + 'MEAS:VOLT?'
            return float(self.root.visa_resource.query(msg))

        @o
        @Action(checks=('not (method == "voltage_status" and'
                        ' self.trigger.mode == "disabled")'),
                values={'method': ('measure', 'trigger_ready',
                                   'voltage_status')}
                )
        def wait_for_settling(self,
                              method: str='measure',
                              stop_on_break: bool=True,
                              break_condition_callable:
                                  Optional[Callable[[], bool]]=None,
                              timeout: float=15,
                              refresh_time: float=1,
                              tolerance: float=1e-5) -> bool:
            """Wait for the output to settle.

            Parameters
            ----------
            method : {'measure', 'trigger_ready', 'voltage_status'}
                Method used to estimate that the target voltage was reached.
                - 'measure': measure the output voltage and compare to target
                  within tolerance (see tolerance)
                - 'trigger_ready': rely on the trigger ready status.
                - 'voltage_status': rely on the voltage status reading, this
                  does work only for triggered settings.

            stop_on_break : bool, optional
                Should the ramp be stopped if the break condition is met. This
                is achieved through a quick measurement of the output followed
                by a setting and a trigger.

            break_condition_callable : Callable, optional
                Callable indicating that we should stop waiting.

            timeout : float, optional
                Time to wait in seconds in addition to the expected condition
                time before breaking.

            refresh_time : float, optional
                Time interval at which to check the break condition.

            tolerance : float, optional
                Tolerance used to determine that the target was reached when
                using the measure method.

            Returns
            -------
            result : bool
                Boolean indicating if the wait succeeded of was interrupted.

            """
            def stop_ramp():
                # We round to ensure that we never get any range issue
                self.voltage = round(self.measure('voltage'), 4)
                self.trigger.fire()

            if method == "measure":
                def has_reached_target():
                    if 'tripped' in self.read_output_status():
                        raise RuntimeError(f'Output {self.ch_id} tripped')
                    return abs(self.voltage - self.measure('voltage'))
            elif method == "trigger_ready":
                def has_reached_target():
                    if 'tripped' in self.read_output_status():
                        raise RuntimeError(f'Output {self.ch_id} tripped')
                    return self.trigger.is_trigger_ready()
            else:
                def has_reached_target():
                    if 'tripped' in self.read_output_status():
                        raise RuntimeError(f'Output {self.ch_id} tripped')
                    return self.read_voltage_status() == 'settled'

            job = InstrJob(has_reached_target, 1, cancel=stop_ramp)
            result = job.wait_for_completion(break_condition_callable,
                                             timeout, refresh_time)
            if not result and stop_on_break:
                job.cancel()
            return result

        # =====================================================================
        # --- Private API -----------------------------------------------------
        # =====================================================================

        @o
        @limit('voltage')
        def _limits_voltage(self):
            """Compute the voltage limits based on range and saturation.

            """
            rng = to_float(self.voltage_range)
            low = max(-rng,
                      float(self.voltage_saturation.low)
                      if self.voltage_saturation.low_enabled else -15)
            high = min(rng, float(self.voltage_saturation.high)
                       if self.voltage_saturation.high_enabled else 15)

            return FloatLimitsValidator(low, high, unit='V')

        @o
        def _header_(self):
            return f'I{self.parent.id};'


class BE210x(BE21xx):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'

    output = channel((0,))

    with output as o:
        #: Set the voltage settling filter. Slow 100 ms, Fast 10 ms
        o.voltage_filter = Str('VOLT:FIL?', 'VOLT:FIL {}',
                               mapping={'Slow': '0', 'Fast': '1'})

        #: Is the remote sensing of the voltage enabled.
        o.remote_sensing = Bool('VOLT:REM?', 'VOLT:REM {:d}',
                                aliases={True: ('ON', 'On', 'on'),
                                         False: ('OFF', 'Off', 'off')})


class BE2101(BE210x):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'


class BE214x(BE21xx):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'

    #: Identity support (we do not use IEEEIdentity because we are not on the
    #: root level).
    identity = subsystem()

    with identity as i:

        #: Format string specifying the format of the IDN query answer and
        #: allowing to extract the following information:
        #: - manufacturer: name of the instrument manufacturer
        #: - model: name of the instrument model
        #: - serial: serial number of the instrument
        #: - firmware: firmware revision
        #: ex {manufacturer},<{model}>,SN{serial}, Firmware revision {firmware}
        i.IEEE_IDN_FORMAT = ('{_:d},"{manufacturer:s} {model:s}B/{_:s}'
                             '/SN{serial:s} LC{_:s} VL{firmware:s}'
                             '\\{_:d}"')

    output = channel((0, 1, 2, 3))

    with output as o:

        o.OUTPUT_STATES = {0: 'enabled',
                           11: 'tripped:main-failure',
                           12: 'tripped:system-failure',
                           17: 'unregulated',
                           18: 'tripped:over-current'}

        o.current_limit_behavior = set_feat(getter=constant('trip'))

        def default_get_feature(self, feat, cmd, *args, **kwargs):
            """Prepend output selection to command.

            """
            cmd = f'C{self.id + 1};' + cmd
            return self.parent.default_get_feature(feat, cmd, *args, **kwargs)

        def default_set_feature(self, feat, cmd, *args, **kwargs):
            """Prepend output selection to command.

            """
            cmd = f'C{self.id + 1};' + cmd
            return self.parent.default_set_feature(feat, cmd, *args, **kwargs)

        o.trigger = subsystem()
        with o.trigger as tr:
            # HINT The BE2141 requires the triggering to be disabled before
            # changing the triggering mode when the output is enabled.
            tr.mode = set_feat(setter='TRIG:IN 0\nTRIG:IN {}')

        @o
        def _header_(self):
            return f'I{self.parent.id};C{self.id};'


class BE2141(BE214x):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'
