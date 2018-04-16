# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""This file is meant to check the working of the driver for the BE2101.

The rack is expected to have a BE2101 in one slot, whose output can be safely
switched on and off and whose output value can vary (and has a large impedance)

"""
# Visa connection info
VISA_RESOURCE_NAME = 'TCPIP::192.168.0.10::5025::SOCKET'

# Index of the slot in which the BE2101 can be found (starting from 1)
MODULE_INDEX = 1

from i3py.drivers.itest import BN100

with BN100(VISA_RESOURCE_NAME) as rack:

    print(rack.be2101.available)

    module = rack.be2101[MODULE_INDEX]
    print(module.identity.manufacturer)
    print(module.identity.model)
    print(module.identity.serial)
    print(module.identity.firmware)

    output = module.output[1]
    for f_name in output.__feats__:
        print(f_name, getattr(output, f_name))

    for sub_name in output.__subsystems__:
        print('testing ', sub_name)
        sub = getattr(output, sub_name)
        for f_name in sub.__feats__:
            print(getattr(sub, f_name))
