# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Standard instaerface of the identity subsystem.

"""
from i3py.core.base_subsystem import SubSystem
from i3py.core.features import Unicode


class Identity(SubSystem):
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
