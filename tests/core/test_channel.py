# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test basic channel instance functionalities.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from i3py.core.declarative import channel
from i3py.core.base_channel import ChannelContainer

from .testing_tools import DummyParent


class ChParent1(DummyParent):

    ch = channel('_list_ch')

    def _list_ch(self):
        return (1, )


class CustomContainer(ChannelContainer):
    pass


class ChParent2(DummyParent):

    ch = channel(('a',), container_type=CustomContainer)


class ChParent3(DummyParent):

    ch = channel(('a',), aliases={0: 'a'})


def test_ch_default_get():

    a = ChParent1()
    ch = a.ch[1]
    ch.default_get_feature(None, 'Test', 1, a=2)
    assert a.d_get_called == 1
    assert a.d_get_cmd == 'Test'
    assert a.d_get_args == (1,)
    assert a.d_get_kwargs == {'id': 1, 'a': 2}


def test_ch_default_set():

    a = ChParent2()
    for ch in a.ch:
        ch.default_set_feature(None, 'Test', 1, a=2)
        assert a.d_set_called == 1
        assert a.d_set_cmd == 'Test'
        assert a.d_set_args == (1,)
        assert a.d_set_kwargs == {'id': 'a', 'a': 2}


def test_custom_container():

    a = ChParent2()
    assert isinstance(a.ch, CustomContainer)


def test_ch_default_check():

    a = ChParent1()
    ch = a.ch[1]
    ch.default_check_operation(None, None, None, None)
    assert a.d_check_instr == 1


def test_ch_lock():
    a = ChParent1()
    ch = a.ch[1]
    assert ch.lock is a.lock


def test_ch_reop():
    a = ChParent1()
    ch = a.ch[1]
    ch.reopen_connection()
    assert a.ropen_called == 1


def test_listing_aliases():
    a = ChParent3()
    aliases = a.ch.aliases
    assert a.ch.aliases is not aliases
    assert a.ch.aliases == aliases


def test_access_through_alias():
    a = ChParent3()
    assert a.ch['a'] is a.ch[0]
