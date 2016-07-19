# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing the register feature.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
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
            Register('a', names=(None,))

    def test_post_get(self):
        r = Register('a', names=('a', 'b', None, 'r', None, None, None, None))
        byte = r.post_get(None, '10')
        assert len(byte) == 8
        assert byte['b'] and byte['r']
        assert not byte['a']
        assert not byte[2]

    def test_pre_set(self):
        r = Register('a', names={'a': 0, 'b': 1, 'r': 15}, length=16)
        assert r.pre_set(None, {'r': True, 'b': False}) == 2**15
