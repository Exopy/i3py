# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""I3py standard for DC sources.

"""
from i3py.core import (HasFeatures, channel, Subsystem, Action)
from i3py.core.features import Bool, Float, Unicode, constant


class DCPowerSource(HasFeatures):
    """Standard interface expected from all DC Power sources.

    """

    #:
    output = channel((0,))

    with output as o:

        #:
        o.enabled = Bool(aliases={True: ['On', 'ON', 'On'],
                                  False: ['Off', 'OFF', 'off']})

        #:
        o.voltage = Float(unit='V')

        #:
        o.voltage_range = Float(unit='V')

        #:
        o.voltage_limit_behavior = Unicode(constant('regulate'),
                                           values=('irrelevant', 'trip',
                                                   'regulate'))

        #:
        o.current = Float(unit='A')

        #:
        o.current_range = Float(unit='A')

        #:
        o.current_limit_behavior = Unicode(constant('regulate'),
                                           values=('irrelevant', 'trip',
                                                   'regulate'))

        @o
        @Action()
        def read_output_status(self):
            """
            """
            pass


class DCPowerSourceWithMeasure(Subsystem):
    """
    """
    #:
    output = channel((0,))

    with output as o:

        @o
        @Action()
        def measure(self, quantity, **kwargs):
            """Measure the output voltage/current.

            Parameters
            ----------
            quantity : unicode, {'voltage', 'current'}
                Quantity to measure.

            **kwargs :
                Optional kwargs to specify the conditions of the measure
                (integration time, averages, etc) if applicable.

            Returns
            -------
            value : float or pint.Quantity
                Measured value. If units are supported the value is a Quantity
                object.

            """
            pass


class DCSourceTriggerSubsystem(Subsystem):
    """
    """
    #:
    mode = Unicode(values=('disabled', 'enabled'))

    #:
    source = Unicode(values=('immediate', 'bus'))  # Will extend later

    #:
    delay = Float(unit='s')

    @Action()
    def arm(self):
        """
        """
        pass


class DCSourceProtectionSubsystem(Subsystem):
    """
    """
    #:
    enabled = Bool(aliases={True: ['On', 'ON', 'On'],
                            False: ['Off', 'OFF', 'off']})

    #:
    behavior = Unicode(constant('trip'))

    #:
    low_level = Float()

    #:
    high_level = Float()

    @Action()
    def read_status(self):
        """
        """
        pass

    @Action()
    def reset(self):
        """
        """
        pass
