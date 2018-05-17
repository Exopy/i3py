# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing the mappings features.

"""
from i3py.core.features.mapping import Mapping
from i3py.core.features.bool import Bool

from .test_feature import TestFeatureInit

class TestMappingInit(TestFeatureInit):

    cls = Mapping

    parameters = dict(mapping={'r': 't'})


def test_mapping():
    m = Mapping(mapping={'On': 1, 'Off': 2})
    assert m.post_get(None, 1) == 'On'
    assert m.post_get(None, 2) == 'Off'

    assert m.pre_set(None, 'On') == 1
    assert m.pre_set(None, 'Off') == 2


def test_mapping_asymetric():
    m = Mapping(mapping=({'On': 'ON', 'Off': 'OFF'}, {'1': 'On', '0': 'Off'}))
    assert m.post_get(None, '1') == 'On'
    assert m.post_get(None, '0') == 'Off'

    assert m.pre_set(None, 'On') == 'ON'
    assert m.pre_set(None, 'Off') == 'OFF'


def test_mapping_asymetric_no_get():
    m = Mapping(mapping=({'On': 'ON', 'Off': 'OFF'}, None))
    assert m.post_get(None, '1') == '1'
    assert m.post_get(None, '0') == '0'

    assert m.pre_set(None, 'On') == 'ON'
    assert m.pre_set(None, 'Off') == 'OFF'


def test_mapping_asymetric_no_set():
    m = Mapping(mapping=(None, {'1': 'On', '0': 'Off'}))
    assert m.post_get(None, '1') == 'On'
    assert m.post_get(None, '0') == 'Off'

    assert m.pre_set(None, 'On') == 'On'
    assert m.pre_set(None, 'Off') == 'Off'


class TestBoolInit(TestFeatureInit):

    cls = Bool

    defaults = dict(mapping={True: 1, False: 2})

    parameters = dict(aliases={True: ['On', 'on', 'ON'],
                               False: ['Off', 'off', 'OFF']})


def test_bool():
    b = Bool(mapping={True: 1, False: 2},
             aliases={True: ['On', 'on', 'ON'], False: ['Off', 'off', 'OFF']})
    assert b.pre_set(None, 'ON') == 1
    assert b.pre_set(None, 'off') == 2
