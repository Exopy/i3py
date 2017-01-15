# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test function composition tools.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import pytest
from funcsigs import signature

from i3py.core.abstracts import AbstractSupportMethodCustomization
from i3py.core.composition import (normalize_signature, MethodComposer,
                                   SupportMethodCustomization,
                                   customize)


def test_normalize_signature():
    """Test that the signature normailzation provide the expected results.

    """
    n_sig = lambda f, alias=None: normalize_signature(signature(f), alias)
    assert n_sig(lambda a, b: 0) == ('a', 'b')
    assert n_sig(lambda a, b: 0, 'c') == ('a', 'b')
    assert n_sig(lambda self, b: 0, 'a') == ('a', 'b')
    assert n_sig(lambda self, *args: 0, 'a') == ('a', '*args')
    assert n_sig(lambda self, **kwargs: 0, 'a') == ('a', '**kwargs')
    assert (n_sig(lambda self, *args, **kwargs: 0, 'b') ==
            ('b', '*args', '**kwargs'))


def helping_func(self, driver, value):
    """Helper function for testing method composition.

    """
    return value + 1


class HelperSupportComp(SupportMethodCustomization):
    """Helper class supporting method customization.

    """
    @property
    def self_alias(self):
        return 'feat'

    def analyse_function(self, meth_name, func, specifiers):
        return specifiers, [], 'value'


class FalseOwner(object):

    def __init__(self):
        super(FalseOwner, self).__init__()
        self.test = FalseMethodCustomizationSupport()


class FalseMethodCustomizationSupport(object):

    def modify_behavior(self, *args):
        self.args = args

AbstractSupportMethodCustomization.register(FalseMethodCustomizationSupport)


def test_cutomize():
    """Test creating and using a customization.

    """
    cs = customize('test', 'm_name')
    owner = FalseOwner()
    f = lambda x: 1
    cs(f)
    cs.customize(owner, 'dd')
    assert owner.test.args == ('m_name', f, (), 'custom')


def test_customize_customize_before_call():
    """Test handling absence of decoration.

    """
    cs = customize('test', 'm_name')
    owner = FalseOwner()
    with pytest.raises(RuntimeError):
        cs.customize(owner, 'dd')

    cs = customize('test', 'm_name', ('remove',))
    owner = FalseOwner()
    cs.customize(owner, 'dd')
    assert owner.test.args == ('m_name', None, ('remove',), 'custom')


def test_customize_customize_wrong_type():
    """Test attempting to customize a descriptor not supporting customization.

    """
    cs = customize('test', 'm_name')
    owner = FalseOwner()
    owner.test = None
    f = lambda x: 1
    cs(f)
    with pytest.raises(AssertionError):
        cs.customize(owner, 'test')


@pytest.fixture
def support_custom():
    """Create an instance of HelperSupportComp.

    """
    return HelperSupportComp()


def test_composer_creation(support_custom):
    """Test creating a composer.

    """
    comp = MethodComposer(support_custom, helping_func, 'feat', 'value')
    assert (tuple(signature(comp.__call__.__func__).parameters) ==
            ('self', 'driver', 'value'))
    comp2 = MethodComposer(support_custom, helping_func, 'feat', 'value')
    assert type(comp) is type(comp2)


@pytest.fixture
def composer(support_custom):
    """Create a method composer for testing.

    """
    return MethodComposer(support_custom, helping_func, 'feat', 'value')


def test_composer_clone(composer):
    """Test cloning a composer.

    """
    new_comp = composer.clone()
    assert new_comp.__self__ is composer.__self__
    assert new_comp.__name__ == composer.__name__
    assert new_comp._alias == composer._alias
    assert new_comp._chain_on == composer._chain_on
    assert new_comp._methods == composer._methods
    assert new_comp._names == composer._names
    assert new_comp._signatures == composer._signatures

    new_comp2 = composer.clone(support_custom())
    assert new_comp2.__self__ is not composer.__self__


def test_composer_modification_methods(composer):
    """Test the composition modification methods.

    """
    assert composer(None, 1) == 2

    def multi(self, driver, value):
        return value * 2
    prep = composer.clone()
    prep.prepend('prep', multi)
    assert prep(None, 2) == 5

    app = composer.clone()
    app.append('app', multi)
    assert app(None, 2) == 6

    def div(self, driver, value):
        return value / 2
    prep.add_after('prep', 'new', div)
    assert prep(None, 2) == 3

    app.add_before('app', 'new', div)
    assert app(None, 2) == 3

    prep.replace('new', multi)
    assert prep(None, 2) == 9

    app.remove('new')
    assert app(None, 2) == 6

    app.reset()
    assert app(None, 1) == 1

    with pytest.raises(ValueError):
        prep.add_after('prep', 'new', div)

    assert prep['prep'] is multi
    assert 'new' in prep

# customize and SupportMethodCustomization are tested on features.
