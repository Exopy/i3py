# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Common tools for the ITest card instruments.

"""

from stringparser import Parser
from i3py.core import Channel, subsystem
from ...base.identity import Identity


def make_card_detector(model_id):
    """Create a function listing the available card of a given model.

    Parameters
    ----------
    model_id : unicode or list of unicode
        Id or ids of the model. ex BE2100

    """
    if isinstance(model_id, list):
        model_id = [m[2:] for m in model_id]
    else:
        model_id = [model_id[2:]]

    def list_channel(driver):
        """Query all the cards fitted on the rack and filter based on the model

        """
        cards = {id: int(i)
                 for card in driver.query('I:L?').split(';')
                 for i, id, _ in card.split(',')}

        return [cards[id] for id in cards if id in model_id]


class BN100Card(Channel):
    """Base driver for cards used with the Bilt BN100 chassis.

    """
    identity = subsystem(Identity)

    with identity as i:

        i.idn_format = ''

        @i
        def _getter(self, feat):
            """Get the identity infos from the *IDN?.

            """
            idn = self.query('*IDN?')
            infos = Parser(self.idn_format)(idn)
            self._cache.update(infos)
            return infos.get(feat.name, '')

        i._get_manufacturer = _getter
        i._get_model = _getter
        i._get_serial = _getter
        i._get_firmware = _getter

    def default_get_feature(self, feat, cmd, *args, **kwargs):
        """Prepend module selection to command.

        """
        cmd = 'I{ch_id};'+cmd
        super(BN100Card, self).default_get_feature(feat, cmd, *args, **kwargs)

    def default_set_feature(self, feat, cmd, *args, **kwargs):
        """Prepend module selection to command.

        """
        cmd = 'I{ch_id};'+cmd
        super(BN100Card, self).default_set_feature(feat, cmd, *args, **kwargs)
