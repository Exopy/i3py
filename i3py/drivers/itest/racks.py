# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Driver for the Itest rack instruments

"""
from i3py.core import channel

from ..common.ieee488 import IEEEReset
from ..common.scpi.error_reading import SCPIErrorReading
from .modules.be21xx import BE2101, BE2141
from .modules import make_card_detector


class BiltMainframe(IEEEReset, SCPIErrorReading):
    """Driver for the Itest BN100 chassis.

    """
    PROTOCOLS = {'TCPIP': {'resource_class': 'SOCKET',
                           'port': '5025'},
                 'GPIB': {'resource_class': 'INSTR'},
                 'ASRL': {'resource_class': 'INSTR'}
                 }

    DEFAULTS = {'COMMON': {'read_termination': '\n',
                           'write_termination': '\n'}
                }

    IEEE_RESET_WAIT = 4

    #: Support for the BE2101 card
    be2101 = channel('_list_be2101', BE2101)

    #: Support for the BE2141 card
    be2141 = channel('_list_be2141', BE2141)

    def initialize(self):
        """Make sure the communication parameters are correctly sets.

        """
        super().initialize()
        self.visa_resource.write('SYST:VERB 0')
        while self.read_error()[0]:
            pass

    _list_be2101 = make_card_detector(['BE2101'])
    _list_be2141 = make_card_detector(['BE2141'])


class BN100(BiltMainframe):
    """Driver for the BN100 Bilt rack.

    """
    __version__ = '0.1.0'


class BN101(BiltMainframe):
    """Driver for the BN101 Bilt rack.

    """
    __version__ = '0.1.0'


class BN103(BiltMainframe):
    """Driver for the BN103 Bilt rack.

    """
    __version__ = '0.1.0'


class BN105(BiltMainframe):
    """Driver for the BN105 Bilt rack.

    """
    __version__ = '0.1.0'
