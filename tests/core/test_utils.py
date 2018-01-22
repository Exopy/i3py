# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing the utility functions (utils.py).

"""
from i3py.core.utils import check_options


def test_check_options_with_dict():
    """Test validating an option specifications based on a dict.

    """
    assert check_options({'opt': {'test': 1, 'bool': 0}}, 'opt["test"]')[0]
    assert not check_options({'opt': {'test': 1, 'bool': 0}}, 'opt["bool"]')[0]
