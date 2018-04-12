# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test basic channel instance functionalities.

"""
import pytest
from i3py.core import channel, customize
from i3py.core.errors import I3pyFailedGet
from i3py.core.base_channel import ChannelContainer, ChannelDescriptor
from i3py.core.features import Options, Str

from .testing_tools import DummyParent, DummyDriver


class ChParent1(DummyParent):

    ch = channel('_list_ch')

    def _list_ch(self):
        return (1, )


class CustomContainer(ChannelContainer):
    pass


class CustomDescriptor(ChannelDescriptor):
    pass


class ChParent2(DummyParent):

    ch = channel(('a',), container_type=CustomContainer)


class ChParent3(DummyParent):

    ch = channel(('a',), aliases={'a': 0, 'b': 1})


class ChOptionsParent(DummyDriver):

        _test_ = True

        options = Options(names={'test': None})

        ch = channel(('a',), options='options["test"]')

        @customize('options', 'get')
        def _get_options(self, driver):
            return {'test': type(driver)._test_}


class ChChecksParent(DummyDriver):

        _test_ = True

        val = Str(True)

        ch = channel(('a',), checks='driver.parent.val == "True"')

        with ch:

            ch.val = Str(True)

            @ch
            @customize('val', 'get')
            def _get(self, driver):
                return 1

        @customize('val', 'get')
        def _get_val(self, driver):
            return type(driver)._test_


def test_ch_default_get():

    a = ChParent1()
    ch = a.ch[1]
    ch.default_get_feature(None, 'Test', 1, a=2)
    assert a.d_get_called == 1
    assert a.d_get_cmd == 'Test'
    assert a.d_get_args == (1,)
    assert a.d_get_kwargs == {'ch_id': 1, 'a': 2}


def test_ch_default_set():

    a = ChParent2()
    for ch in a.ch:
        ch.default_set_feature(None, 'Test', 1, a=2)
        assert a.d_set_called == 1
        assert a.d_set_cmd == 'Test'
        assert a.d_set_args == (1,)
        assert a.d_set_kwargs == {'ch_id': 'a', 'a': 2}


def test_custom_container():

    a = ChParent2()
    assert isinstance(a.ch, CustomContainer)


def test_custom_descriptor():

    class ChParent(DummyParent):

        ch = channel(('a',), descriptor_type=CustomDescriptor)

    assert isinstance(ChParent.__dict__['ch'], CustomDescriptor)


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


def test_accessing_non_existing_channel():
    a = ChParent3()
    with pytest.raises(KeyError):
        a.ch['b']
    with pytest.raises(KeyError):
        a.ch[1]


def test_ch_options():
    """Test the handling of options at the level of subsystems.

    """
    p = ChOptionsParent()
    ChOptionsParent._test_ = True
    p.ch  # Option is True should not have any issue accessing it

    ChOptionsParent._test_ = False

    p = ChOptionsParent()
    with pytest.raises(AttributeError):
        p.ch


def test_ch_checks():
    """Test the handling of checks at the level of a subsystem.

    """
    ChChecksParent._test_ = True
    p = ChChecksParent()
    assert p.ch['a'].val == '1'

    p.clear_cache()
    ChChecksParent._test_ = False
    with pytest.raises(I3pyFailedGet):
        p.ch['a'].val


def test_ch_inherited_options():
    """Test that options are properly inherited.

    """
    class ChOptionsParent2(ChOptionsParent):

        ch = channel(('a',))

    assert ChOptionsParent.ch is not ChOptionsParent2.ch

    ChOptionsParent2._test_ = True
    p = ChOptionsParent2()
    p.ch  # Option is True should not have any issue accessing it

    ChOptionsParent2._test_ = False
    p = ChOptionsParent2()
    with pytest.raises(AttributeError):
        p.ch


def test_ch_inherited_checks():
    """Test that options are properly inherited.

    """
    class ChChecksParent2(ChChecksParent):

        ch = channel()

    assert ChChecksParent.ch is not ChChecksParent2.ch

    ChChecksParent2._test_ = True
    p = ChChecksParent2()
    assert p.ch['a'].val == '1'

    p.clear_cache()
    ChChecksParent2._test_ = False
    with pytest.raises(I3pyFailedGet):
        p.ch['a'].val
