# -*- coding: utf-8 -*-
"""
    lantz_drivers.bilt.cards.be2100
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Driver for the Bilt BE2100 card : high stability DC voltage source.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from lantz_core import set_feat, subsystem, channel, Action
from lantz_core.features import Float, Unicode, constant
from lantz_core.limits import FloatLimitsValidator
from lantz_core.unit import to_float

from .common import BN100Card, make_card_detector
from ...base.dc_sources import (DCPowerSourceWithMeasure,
                                DCSourceTriggerSubsystem)


detect_be2100 = make_card_detector(['BE2101', 'BE2102', 'BE2103'])


# Add identity parsing
class BE2100(BN100Card, DCPowerSourceWithMeasure):
    """Driver for the Bilt BE2100 high precision dc voltage source.

    """
    output = channel()

    with output as o:
        o.enabled = set_feat(getter='OUT?', setter='OUT {}')

        o.voltage = set_feat(getter='VOLT?', setter='VOLT {:E}',
                             limits='voltage')

        o.voltage_range = set_feat(getter='VOLT:RANG?', setter='VOLT:RANG {}',
                                   values=(1.2, 12), extract='{},{_}',
                                   checks=(None, 'not driver.output'),
                                   discard={'features': ('voltage',),
                                            'limits': ('voltage',)})

        o.voltage_limit_behavior = set_feat(getter=constant('irrelevant'))

        #: Set the voltage settling filter. Slow 100 ms, Fast 10 ms
        o.voltage_filter = Unicode('VOLT:FILT?', 'VOLT:FILT {}',
                                   mapping={'Slow': 0, 'Fast': 1})

        #: Specify stricter voltage limitations than the ones linked to the
        #: range.
        o.voltage_saturation = subsystem()
        with o.voltage_saturation as vs:
            #: Lowest allowed voltage.
            vs.low = Float('VOLT:SAT:NEG?', 'VOLT:SAT:NEG {}', unit='V',
                           limits=(-12, 0), discard={'limits': ('voltage',)})

            #: Highest allowed voltage.
            vs.high = Float('VOLT:SAT:POS?', 'VOLT:SAT:POS {}', unit='V',
                            limits=(-12, 0), discard={'limits': ('voltage',)})

        o.current = set_feat(getter=constant(0.2))

        o.current_range = set_feat(getter=constant(0.2))

        o.current_limit_behavior = set_feat(getter=constant('regulate'))

        #: Subsystem handling triggering and reaction to triggering.
        o.trigger = subsystem(DCSourceTriggerSubsystem)
        with o.trigger as tr:
            #: Type of response to triggering :
            #: - disabled : immediate update of voltage everytime the voltage
            #:   feature is
            #:   updated.
            #: - slope : update after receiving a trigger based on the slope
            #:   value.
            #: - stair : update after receiving a trigger using step_amplitude
            #:   and step_width.
            #: - step : increment by one step_amplitude till target value for
            #:   each triggering.
            #: - auto : update after receiving a trigger by steps but
            #:   determining when to move to next step based on voltage
            #:   sensing.
            tr.mode = Unicode('TRIG:IN?', 'TRIG:IN {}',
                              mapping={'disabled': '0', 'slope': '1',
                                       'stair': '2', 'step': '4', 'auto': '5'})

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

# XXXX
        @o
        @Action()
        def read_output_status(self):
            """
            """
            pass

        @o
        @Action()
        def read_voltage_status(self):
            """Progression of the current voltage update.

            Returns
            -------
            progression : int
                Progression of the voltage update. The value is between 0
                and 1.

            """
            return int(self.query('I {};VOLT:STAT?'.format(self.ch_id)))

        # XXXX
        @o
        @Action(unit=())
        def measure(self, kind, **kwargs):
            """
            """
            if kind != 'voltage':
                raise ValueError('')

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

    @Action
    def fire_trigger(self):
        """Send a software trigger.

        """
        self.write('I {};TRIG:IN:INIT'.format(self.ch_id))
