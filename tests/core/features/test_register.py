# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing the register feature.

"""
from pytest import raises

from i3py.core.features.register import Register

from .test_mappings import TestMappingInit


class TestRegisterInit(TestMappingInit):

    cls = Register

    defaults = dict(names=('a', 'b', None, 'r', None, None, None, None))

    parameters = dict(length=8)

    exclude = ['mapping']


class TestRegister(object):

    def test_init(self):
        with raises(ValueError):
            Register('a', names=(None,)).__set_name__(None, 'test')

    def test_post_get(self):
        r = Register('a', names=('a', 'b', None, 'r', None, None, None, None))
        r.__set_name__(None, 'test')
        byte = r.post_get(None, '10')
        assert byte & byte.b and byte & byte.r
        assert not byte & byte.a
        assert not byte & r.flag.BIT_2

    def test_pre_set(self):
        r = Register('a', names={'a': 0, 'b': 1, 'r': 15}, length=16)
        r.__set_name__(None, 'test')
        assert r.pre_set(None, r.flag.r) == 2**15
