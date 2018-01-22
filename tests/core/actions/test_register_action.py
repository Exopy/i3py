# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing the RegisterAction.

"""
import pytest

from i3py.core.actions import RegisterAction
from ..testing_tools import DummyParent


def test_register_action_with_name_list():
    """Test that we handle properly a name list.

    """
    class RegTest(DummyParent):

        @RegisterAction(('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'))
        def reg(self):
            return 2**3 + 2**5

    reg = RegTest().reg()
    assert reg.pop('d') and reg.pop('f')
    assert not any(reg.values())


def test_register_action_with_name_dict():
    """Test that we handle properly a name dict.

    """
    class RegTest(DummyParent):

        @RegisterAction({'c': 3, 'e': 5}, length=16)
        def reg(self):
            return 2**3 + 2**5

    reg = RegTest().reg()
    assert len(reg) == 16
    assert reg.pop('c') and reg.pop('e')
    assert not any(reg.values())


def test_register_action_wrong_length():
    """Test we raise on length issue.

    """
    with pytest.raises(ValueError):
        RegisterAction(('a', 'b'))
