# -*- coding: utf-8 -*-
"""
    lantz_drivers.base.identity
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Definition of the standard identity subsystem.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from lantz_core.has_features import Subsystem
from lantz_core.features import Unicode


class Identity(Subsystem):
    """Standard subsystem defining the expected identity infos.

    This should be used as a base class for the identity subsystem of
    instruments providing identity informations.

    Notes
    -----
    Somes of those infos might not be available for a given instrument. In such
    a case the Feature should return ''.

    """
    #: Manufacturer as returned by the instrument.
    manufacturer = Unicode()

    #: Model name as returned by the instrument.
    model = Unicode()

    #: Instrument serial number.
    serial = Unicode()

    #: Version of the installed firmware.
    firmware = Unicode()
