# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base class for instrument using a binary registry.

"""
from ...core import subsystem
from .base import BaseVisaDriver, VisaAction


class VisaRegistryDriver(BaseVisaDriver):
    """Base class for driver based on VISA and a binary registry.

    This covers among others PXI, ...

    """
    #: Direct access to the visa resource.
    visa_resource = subsystem()

    with visa_resource as vr:

        @vr
        @VisaAction()
        def read_memory(self, space, offset, width, extended=False):
            """See Pyvisa docs.

            """
            return self.parent._resource.read_memory(space, offset, width,
                                                     extended)

        @vr
        @VisaAction()
        def write_memory(self, space, offset, data, width, extended=False):
            """See Pyvisa docs.

            """
            return self.parent._resource.write_memory(space, offset, data,
                                                      width, extended)

        @vr
        @VisaAction()
        def move_in(self, space, offset, length, width, extended=False):
            """See Pyvisa docs.

            """
            return self.parent._resource.move_in(space, offset, length, width,
                                                 extended)

        @vr
        @VisaAction()
        def move_out(self, space, offset, length, data, width, extended=False):
            """See Pyvisa docs.

            """
            return self.parent._resource.move_out(space, offset, length, data,
                                                  width, extended)
