# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tests for the LimitsValidated helper class.

"""
import pytest

from i3py.core.declarative import limit
from i3py.core.features.limits_validated import LimitsValidated
from i3py.core.limits import IntLimitsValidator

from ..testing_tools import DummyParent
from .test_feature import TestFeatureInit


class TestLimitsValidatedInit(TestFeatureInit):
    """Test LimitsValidated init.

    """
    cls = LimitsValidated

    parameters = dict(limits='test')


def test_with_no_limits():
    """Test having no limits.

    """
    feat = LimitsValidated(setter=True)
    assert feat.pre_set(None, 1) == 1


def test_with_validator():
    """Test creating a LimitsValidated by passing it a validator.

    """
    feat = LimitsValidated(setter=True, limits=IntLimitsValidator(0, 10))
    assert feat.pre_set(None, 1) == 1
    with pytest.raises(ValueError):
        feat.pre_set(None, -1)


def test_with_name():
    """Test creating a LimitsValidated querying the limit by name.

    """
    class LimitsHolder(DummyParent):

        n = 0

        @limit('test')
        def _limits_test(self):
            self.n += 1
            return IntLimitsValidator(self.n)

    o = LimitsHolder()
    i = LimitsValidated(setter=True, limits='test')
    assert i.pre_set(o, 1)
    with pytest.raises(ValueError):
        i.pre_set(o, 0)
    o.discard_limits(('test', ))
    with pytest.raises(ValueError):
        i.pre_set(o, 1)


def test_type_error_handling():
    """Test handling of bad type of limits.

    """
    with pytest.raises(TypeError):
        LimitsValidated(setter=True, limits=(1, 2))
