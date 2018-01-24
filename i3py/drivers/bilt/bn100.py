# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Driver for the ITest BN100 rack instrument

"""
from i3py.core import channel

from ..common.scpi.error_reading import SCPIErrorReading
from ..common.ieee488 import IEEEReset
from .cards.be2100 import BE2100, detect_be2100


class BN100(IEEEReset, SCPIErrorReading):
    """Driver for the Bilt BN100 chassis.

    """

    PROTOCOLS = {'TCPIP': '5025::SOCKET'}

    DEFAULTS = {'COMMON': {'read_termination': '\n',
                           'write_termination': '\n'}
                }

    be2100 = channel('_list_be2100', BE2100)

    IEEE_RESET_WAIT = 4

    def initialize(self):
        """Make sure the communication parameters are correctly sets.

        """
        super(BN100, self).initialize()
        self.write('SYST:VERB 0')

    _list_be2100 = detect_be2100
