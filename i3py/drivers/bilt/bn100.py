# -*- coding: utf-8 -*-
"""
    lantz_drivers.bilt.bn100
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Driver for the Bilt BN100 chassis.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from lantz_core.has_features import channel

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
