# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tests for the tools to customize feature and help in their writings.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import pytest

from i3py.core.features.factories import constant, conditional
from ..testing_tools import DummyParent


class TestMethodsComposer(object):

    def setup(self):

        self.composer = MethodsComposer()
        self.composer._names = ['test1', 'test2']
        self.first = lambda x: x
        self.second = lambda x: 2*x
        self.composer._methods = [self.first, self.second]

    def test_clone(self):
        new = self.composer.clone()
        assert new._names == self.composer._names
        assert new._names is not self.composer._names
        assert new ._methods == self.composer._methods
        assert new._methods is not self.composer._methods

    def test_append(self):
        app = lambda x: x**2
        self.composer.append('append', app)
        assert self.composer._names[-1] == 'append'
        assert self.composer._methods[-1] is app

    def test_prepend(self):
        pre = lambda x: x**2
        self.composer.prepend('prepend', pre)
        assert self.composer._names[0] == 'prepend'
        assert self.composer._methods[0] is pre

    def test_add_before(self):
        bef = lambda x: x**2
        self.composer.add_before('test2', 'before', bef)
        assert self.composer._names[1] == 'before'
        assert self.composer._methods[1] is bef

    def test_add_after(self):
        after = lambda x: x**2
        self.composer.add_after('test1', 'after', after)
        assert self.composer._names[1] == 'after'
        assert self.composer._methods[1] is after

    def test_remove(self):
        app = lambda x: x**2
        self.composer.append('append', app)
        self.composer.remove('test1')
        assert 'test1' not in self.composer
        assert self.first not in self.composer._methods

    def test_replace(self):
        rep = lambda x: x**2
        self.composer.replace('test1', rep)
        assert self.first is not self.composer._methods[0]
        assert rep is self.composer._methods[0]

    def test_reset(self):
        self.composer.reset()
        assert not self.composer._names
        assert not self.composer._methods

    def test_getitem(self):
        assert self.composer['test1'] is self.first

    def test_overwritting_id(self):
        rep = lambda x: x**2
        self.composer.append('test1', rep)
        assert self.composer._names == ['test2', 'test1']


def assert_val(val):
    assert val


def test_pre_get_composer():

    composer = PreGetComposer()
    composer._methods = [lambda x: 1, lambda x: assert_val(False)]

    with pytest.raises(AssertionError):
        composer(None)


def test_post_get_composer():

    composer = PostGetComposer()
    composer._methods = [lambda d, x: x*2, lambda d, x: x+1]

    assert composer(None, 1) == 3


def test_pre_set_composer():

    composer = PreSetComposer()
    composer._methods = [lambda d, x: x*2, lambda d, x: x+1]

    assert composer(None, 1) == 3


def test_post_set_composer():

    composer = PostSetComposer()
    composer._methods = [lambda d, x, i, r: assert_val(x == 1),
                         lambda d, x, i, r: assert_val(i == 2),
                         lambda d, x, i, r: assert_val(r == 3)]

    composer(None, 1, 2, 3)


def test_constant():
    """Test creating a constant getter.

    """
    builder = constant(True)
    f = builder.build_getter()
    assert f(None, None) is True


def test_conditional_getter():
    """Test creating a conditional setter.

    """
    dummy = DummyParent()
    dummy.state = False

    # not using default
    builder = conditional('1 if driver.state else 2')
    f = builder.build_getter()
    assert f(None, dummy) == 2
    assert not dummy.d_get_cmd
    dummy.state = True
    assert f(None, dummy) == 1
    assert not dummy.d_get_cmd

    # using default
    builder = conditional('1 if driver.state else 2', default=True)
    f = builder.build_getter()
    assert f(None, dummy) == 1
    assert dummy.d_get_cmd == 1
    dummy.state = False
    assert f(None, dummy) == 2
    assert dummy.d_get_cmd == 2


def test_conditional_setter():
    """Test creating a conditional setter.

    """
    dummy = DummyParent()
    dummy.state = True

    builder = conditional('1 if driver.state else 2')
    with pytest.raises(ValueError):
        builder.build_setter()

    builder = conditional('"test" if driver.state else "bis"', True)
    f = builder.build_setter()
    f(None, dummy, 1)
    assert dummy.d_set_cmd == "test"
    dummy.state = False
    f(None, dummy, 1)
    assert dummy.d_set_cmd == "bis"
