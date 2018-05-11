# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""This file is meant to check the working of the driver for the BE2141.

The rack is expected to have a BE2101 in one slot, whose output can be safely
switched on and off and whose output value can vary (and has a large impedance)

"""
# Visa connection info
VISA_RESOURCE_NAME = 'TCPIP::192.168.0.10::5025::SOCKET'

# Index of the slot in which the BE2101 can be found (starting from 1)
MODULE_INDEX = 1

from i3py.core.errors import I3pyFailedCall, I3pyFailedSet
from i3py.drivers.itest import BN100

with BN100(VISA_RESOURCE_NAME) as rack:

    # Test reading all features
    print('Available modules', rack.be2141.available)

    module = rack.be2141[MODULE_INDEX]
    print('Manufacturer', module.identity.manufacturer)
    print('Model', module.identity.model)
    print('Serial number', module.identity.serial)
    print('Firmware', module.identity.firmware)

    print('Testing output')
    output = module.output[0]
    for f_name in output.__feats__:
        print('    ', f_name, getattr(output, f_name))

    for sub_name in output.__subsystems__:
        print('  Testing ', sub_name)
        sub = getattr(output, sub_name)
        for f_name in sub.__feats__:
            print('      ', f_name, getattr(sub, f_name))

    # Test action reading basic status
    print('Output status', output.read_output_status())
    output.clear_output_status()
    print('Measured output voltage', output.measure('voltage'))

    # Test settings and general behavior
    print('Setting ouputs')
    output.voltage_saturation.low_enabled = False
    output.voltage_saturation.high_enabled = False
    print('Known limits', output.declared_limits)
    output.trigger.mode = 'disabled'
    output.voltage_range = 1.2
    output.enabled = True
    output.voltage = 1.0
    try:
        output.read_voltage_status()
    except I3pyFailedCall:
        print('Cannot read voltage status in non-triggered mode')
    try:
        output.wait_for_settling()
    except I3pyFailedCall:
        print('Cannot wait for settling in non-triggered mode')

    # XXX test the other trigger modes
    output.trigger.mode = 'slope'
    output.trigger.slope = 0.01
    output.voltage = 0.5
    output.trigger.fire()
    output.wait_for_settling()
    print(output.measure('voltage'))

    output.voltage_saturation.low_enabled = True
    output.voltage_saturation.high_enabled = True
    output.voltage_saturation.low = -0.5
    output.voltage_saturation.high = 0.4
    print('New voltage', output.voltage)
    try:
        output.voltage = -0.6
    except I3pyFailedSet:
        print('New restriction on the gate voltage')
