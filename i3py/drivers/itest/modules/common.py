# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Common tools for the Bilt module instruments.

"""
from typing import Any, Callable, List, Union

from i3py.core import Channel, subsystem

from ...base.identity import Identity


def make_card_detector(model_id: Union[str, List[str]]
                       ) -> Callable[[Any], List[str]]:
    """Create a function listing the available card of a given model.

    Parameters
    ----------
    model_id : str or list of str
        Id or ids of the model. ex BE2101

    """
    if not isinstance(model_id, list):
        model_id = [model_id]

    # We strip the leading BE
    model_id = set(m.strip('BE') for m in model_id)

    def list_channel(driver):
        """Query all the cards fitted on the rack and filter based on the model

        """
        cards = {int(i): id
                 for i, id in [card.split(',')
                               for card in driver.query('I:L?').split(';')]}

        return [index for index in cards if cards[index] in model_id]

    return list_channel


class BiltModule(Channel):
    """Base driver for module used with the Bilt chassis.

    """
    identity = subsystem(Identity)

    with identity as i:
        pass

    def default_get_feature(self, feat, cmd, *args, **kwargs):
        """Prepend module selection to command.

        """
        cmd = 'I{ch_id};'+cmd
        super().default_get_feature(feat, cmd, *args, **kwargs)

    def default_set_feature(self, feat, cmd, *args, **kwargs):
        """Prepend module selection to command.

        """
        cmd = 'I{ch_id};'+cmd
        super().default_set_feature(feat, cmd, *args, **kwargs)
