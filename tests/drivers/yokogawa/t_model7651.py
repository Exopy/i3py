# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""This file is meant to check the working of the driver for the 7651.

The instrument is expected to be in a situation where output can be safely
switched on and off and whose output value can vary (and has a large impedance)

"""
# Visa connection info
VISA_RESOURCE_NAME = 'GPIB0::5::INSTR'

from time import sleep
from i3py.core.errors import I3pyFailedCall, I3pyFailedSet
from i3py.drivers.yokogawa import Model7651

with Model7651(VISA_RESOURCE_NAME) as driver:

    # Test reading all features
    assert driver.is_connected()
    print('Manufacturer', driver.identity.manufacturer)
    print('Model', driver.identity.model)
    print('Serial number', driver.identity.serial)
    print('Firmware', driver.identity.firmware)

    print('Testing output')
    output = driver.output[0]
    for f_name in output.__feats__:
        print('    ', f_name, getattr(output, f_name))

    for sub_name in output.__subsystems__:
        print('  Testing ', sub_name)
        sub = getattr(output, sub_name)
        for f_name in sub.__feats__:
            print('      ', f_name, getattr(sub, f_name))

    # Test action reading basic status
    print('Output status', output.read_output_status())

    # Test voltage mode
    print('Voltage mode')
    output.enabled = False
    output.mode = 'voltage'
    print(output.check_cache())
    print('Known limits', output.declared_limits)
    output.voltage_range = 1
    output.enabled = True
    output.voltage = 1.0
    output.current = 0.1
    sleep(1)
    assert output.read_output_status() == 'enabled:constant-voltage'

    # Test current mode
    print('Current mode')
    output.mode = 'current'
    print(output.check_cache())
    assert not output.enabled
    output.current = 0
    output.enabled = True
    output.current_range = 0.1
    output.voltage = 10
    output.current = 0.05
    sleep(1)
    assert output.read_output_status() == 'enabled:constant-voltage'
