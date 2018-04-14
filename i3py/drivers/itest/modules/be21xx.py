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
from typing import Optional, Callable

from i3py.core import FloatLimitsValidator, channel, set_feat, subsystem
from i3py.core.actions import Action
from i3py.core.features import Float, Str, constant
from i3py.core.job import InstrJob
from i3py.core.unit import to_float, FLOAT_QUANTITY

from ...common.ieee488 import IEEEIdentity
from ...base.dc_sources import (DCPowerSourceWithMeasure,
                                DCSourceTriggerSubsystem)
from .common import BiltModule


class BE21xx(BiltModule, DCPowerSourceWithMeasure, IEEEIdentity):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'

    # Identity support.
    identity = subsystem()
    with identity as i:
        i.IEEE_IDN_FORMAT = ('{_:d}, "{manufacturer:s} {model:s}BB/{_:s}'
                             '\\{serial:s} LC{_:s} VL{firmware:s}\\{_:d}')

    # DC outputs
    output = channel((0,))

    with output as o:
        o.enabled = set_feat(getter='OUT?', setter='OUT {}')

        o.voltage = set_feat(getter='VOLT?', setter='VOLT {:E}',
                             limits='voltage')

        o.voltage_range = set_feat(getter='VOLT:RANG?', setter='VOLT:RANG {}',
                                   values=(1.2, 12), extract='{},{_}',
                                   checks=(None, 'not driver.output'),
                                   discard={'features': ('voltage',),
                                            'limits': ('voltage',)})

        #: Specify stricter voltage limitations than the ones linked to the
        #: range.
        o.voltage_saturation = subsystem()
        with o.voltage_saturation as vs:
            #: Lowest allowed voltage.
            vs.low = Float('VOLT:SAT:NEG?', 'VOLT:SAT:NEG {}', unit='V',
                           limits=(-12, 0), discard={'limits': ('voltage',)})

            #: Highest allowed voltage.
            vs.high = Float('VOLT:SAT:POS?', 'VOLT:SAT:POS {}', unit='V',
                            limits=(0, 12), discard={'limits': ('voltage',)})

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
                                       unit='V', limits='voltage')

            @Action()
            def fire(self):
                """Send a software trigger.

                """
                self.root.visa_resource.write(f'I {self.ch_id};TRIG:IN:INIT')

        # XXX todo
        @o
        @Action()
        def read_output_status(self) -> str:
            """Determine the current status of the output.

            """
            answer = self.root.visa_resource.query('LIM:FAIL?')

        @o
        @Action()
        def read_voltage_status(self) -> str:
            """Progression of the current voltage update.

            Returns
            -------
            progression : int
                Progression of the voltage update. The value is between 0
                and 1.

            """
            msg = f'I {self.parent.ch_id};VOLT:STAT?'
            if int(self.root.visa_resource.query(msg)) == 1:
                return 'settled'
            else:
                return 'changing'

        @o
        @Action(unit=((None, None, None), 'V'))
        def measure(self, kind, **kwargs) -> FLOAT_QUANTITY:
            """Measure the output voltage.

            """
            if kind != 'voltage':
                raise ValueError('')
            else:
                return float(self.query(f'I{self.parent.ch_id};MEAS:VOLT?'))

        @o
        @Action()
        def wait_for_settling(self,
                              break_condition_callable:
                                  Optional[Callable[[], bool]]=None,
                              timeout: float=15,
                              refresh_time: float=1) -> bool:
            """Wait for the output to settle.

             Parameters
            ----------
            break_condition_callable : Callable, optional
                Callable indicating that we should stop waiting.

            timeout : float, optional
                Time to wait in seconds in addition to the expected condition
                time before breaking.

            refresh_time : float, optional
                Time interval at which to check the break condition.

            Returns
            -------
            result : bool
                Boolean indicating if the wait succeeded of was interrupted.

            """
            job = InstrJob(lambda: self.read_voltage_status() == 'settled', 1)
            return job.wait_for_completion(break_condition_callable,
                                           timeout, refresh_time)

        # =====================================================================
        # --- Private API -----------------------------------------------------
        # =====================================================================

        @o
        def _limits_voltage(self):
            """Compute the voltage limits based on range and saturation.

            """
            rng = to_float(self.voltage_range)
            low = max(-rng, float(self.voltage_saturation.low))
            high = min(rng, float(self.voltage_saturation.high))

            step = 1.2e-6 if rng == 1.2 else 1.2e-5

            return FloatLimitsValidator(low, high, step, 'V')


class BE210x(BiltModule, DCPowerSourceWithMeasure, IEEEIdentity):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'

    output = channel((0,))

    with output as o:
        #: Set the voltage settling filter. Slow 100 ms, Fast 10 ms
        o.voltage_filter = Str('VOLT:FILT?', 'VOLT:FILT {}',
                               mapping={'Slow': 0, 'Fast': 1})


class BE2101(BiltModule, DCPowerSourceWithMeasure, IEEEIdentity):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'


class BE214x(BE21xx):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'

    output = channel((0, 1, 2, 3))


class BE2141(BE214x):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    __version__ = '0.1.0'
