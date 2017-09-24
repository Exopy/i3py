# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tests for the Alias feature.

"""
import pytest

from i3py.core.composition import customize
from i3py.core.has_features import subsystem
from i3py.core.features import Bool
from i3py.core.features.alias import Alias

from ..testing_tools import DummyParent


@pytest.fixture
def tester():
    class AliasTester(DummyParent):

        state = Bool(True, True, mapping={True: True, False: False})
        _state = False

        r_alias = Alias('state')

        sub = subsystem()

        with sub as s:
            s.rw_alias = Alias('.state', True)

        @customize('state', 'get')
        def _get_state(feat, driver):
            return driver._state

        @customize('state', 'set')
        def _set_state(feat, driver, value):
            driver._state = value

    return AliasTester()


def test_alias_on_same_level(tester):

    assert tester.r_alias is False
    tester.state = True
    assert tester.r_alias is True

    with pytest.raises(AttributeError):
        tester.r_alias = False


def test_alias_on_parent(tester):

    assert tester.sub.rw_alias is False
    tester.state = True
    assert tester.sub.rw_alias is True

    tester.sub.rw_alias = False
    assert tester.state is False
