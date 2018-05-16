# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""This file is meant to check the working of the driver for the E3631A.

The instrument is expected to be in a situation where output can be safely
switched on and off and whose output value can vary (and has a large impedance)

"""
# Visa connection info
VISA_RESOURCE_NAME = 'GPIB::2::INSTR'

from i3py.core.errors import I3pyFailedCall, I3pyFailedSet
from i3py.drivers.keysight import E3631A

with E3631A(VISA_RESOURCE_NAME) as driver:

    # Test reading all features
    print('Manufacturer', driver.identity.manufacturer)
    print('Model', driver.identity.model)
    print('Serial number', driver.identity.serial)
    print('Firmware', driver.identity.firmware)

    print('Outputs enabled', driver.outputs_enabled)
    print('Coupled triggers', driver.coupled_triggers)
    print('Outputs tracking', driver.outputs_tracking)

    print('Testing output')
    for output in driver.outputs:
        for f_name in output.__feats__:
            print('    ', f_name, getattr(output, f_name))

        for sub_name in output.__subsystems__:
            print('  Testing ', sub_name)
            sub = getattr(output, sub_name)
            for f_name in sub.__feats__:
                print('      ', f_name, getattr(sub, f_name))

        # Test action reading basic status
        print('Output status', output.read_output_status())
        print('Measured output voltage', output.measure('voltage'))
        print('Measured output current', output.measure('current'))

    # TODO add more comprehensive tests
