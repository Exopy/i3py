# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test basic subsystem instance functionalities.

"""
import pytest

from i3py.core import subsystem, customize
from i3py.core.actions import Action
from i3py.core.base_subsystem import SubSystemDescriptor
from i3py.core.features import Options, Str
from i3py.core.errors import I3pyFailedGet, I3pyFailedCall
from .testing_tools import DummyParent, DummyDriver


class CustomDescriptor(SubSystemDescriptor):
    pass


class SSParent(DummyParent):

    ss = subsystem()


class SSOptionsParent(DummyDriver):

        _test_ = True

        options = Options()

        ss = subsystem(options='options["test"]')

        @customize('options', 'get')
        def _get_options(self, driver):
            return {'test': type(driver)._test_}


class SSChecksParent(DummyDriver):

        _test_ = True

        val = Str(True)

        ss = subsystem(checks='driver.parent.val == "True"')

        with ss:

            ss.val = Str(True)

            @ss
            @customize('val', 'get')
            def _get(self, driver):
                return 1

            @ss
            @Action()
            def func(self):
                return 1

        @customize('val', 'get')
        def _get_val(self, driver):
            return type(driver)._test_


def test_ss_d_get():

    a = SSParent()
    a.ss.default_get_feature(None, 'Test', 1, a=2)
    assert a.d_get_called == 1
    assert a.d_get_cmd == 'Test'
    assert a.d_get_args == (1,)
    assert a.d_get_kwargs == {'a': 2}


def test_ss_d_set():
    a = SSParent()
    a.ss.default_set_feature(None, 'Test', 1, a=2)
    assert a.d_set_called == 1
    assert a.d_set_cmd == 'Test'
    assert a.d_set_args == (1,)
    assert a.d_set_kwargs == {'a': 2}


def test_ss_d_check():
    a = SSParent()
    a.ss.default_check_operation(None, None, None, None)
    assert a.d_check_instr == 1


def test_ss_lock():
    a = SSParent()
    assert a.ss.lock is a.lock


def test_ss_reop():
    a = SSParent()
    a.ss.reopen_connection()
    assert a.ropen_called == 1


def test_ss_custom_descriptor():
    """Test specifying a custom descriptor.

    """

    class SSParent(DummyParent):

        ss = subsystem(descriptor_type=CustomDescriptor)

    assert isinstance(SSParent.__dict__['ss'], CustomDescriptor)


def test_ss_options():
    """Test the handling of options at the level of subsystems.

    """
    p = SSOptionsParent()
    SSOptionsParent._test_ = True
    p.ss  # Option is True should not have any issue accessing it

    SSOptionsParent._test_ = False

    p = SSOptionsParent()
    with pytest.raises(AttributeError):
        p.ss


def test_ss_checks():
    """Test the handling of checks at the level of a subsystem.

    """
    SSChecksParent._test_ = True
    p = SSChecksParent()
    assert p.ss.val == '1'
    assert p.ss.func() == 1

    p.clear_cache()
    SSChecksParent._test_ = False
    with pytest.raises(I3pyFailedGet):
        p.ss.val
    with pytest.raises(I3pyFailedCall):
        p.ss.func()


def test_checks_on_parent_ss():
    """Test that a subsystem check the enabling condition of all its parents.

    """
    class NestedSS(SSChecksParent):

        _test2_ = True

        ss = subsystem()

        with ss:

            ss.val2 = Str(True)

            @ss
            @customize('val2', 'get')
            def _get_val2(self, driver):
                return type(driver.parent)._test2_

            ss.ss1 = subsystem()

            with ss.ss1 as s1:
                s1.val = Str(True)

                @s1
                @customize('val', 'get')
                def _get(self, driver):
                    return 1

                @s1
                @Action()
                def func(self):
                    return 1

            ss.ss2 = subsystem(checks='driver.parent.val2 == "True"')

            with ss.ss2 as s2:

                s2.val = Str(True)

                @s2
                @customize('val', 'get')
                def _get(self, driver):
                    return 1

                @s2
                @Action()
                def func(self):
                    return 1

    NestedSS._test_ = True
    p = NestedSS()
    assert p.ss.val == '1'
    assert p.ss.ss1.val == '1'
    assert p.ss.ss2.val == '1'

    p.clear_cache()
    NestedSS._test2_ = False
    with pytest.raises(I3pyFailedGet):
        p.ss.ss2.val
    with pytest.raises(I3pyFailedCall):
        p.ss.ss2.func()

    p.clear_cache()
    NestedSS._test_ = False
    NestedSS._test2_ = True
    with pytest.raises(I3pyFailedGet):
        p.ss.val
    with pytest.raises(I3pyFailedCall):
        p.ss.func()
    with pytest.raises(I3pyFailedGet):
        p.ss.ss1.val
    with pytest.raises(I3pyFailedCall):
        p.ss.ss1.func()
    with pytest.raises(I3pyFailedGet):
        p.ss.ss2.val
    with pytest.raises(I3pyFailedCall):
        p.ss.ss2.func()


def test_ss_inherited_options():
    """Test that options are properly inherited.

    """
    class SSOptionsParent2(SSOptionsParent):

        ss = subsystem()

    assert SSOptionsParent.ss is not SSOptionsParent2.ss

    p = SSOptionsParent2._test_ = True
    p = SSOptionsParent2()
    p.ss  # Option is True should not have any issue accessing it

    SSOptionsParent2._test_ = False

    p = SSOptionsParent2()
    with pytest.raises(AttributeError):
        p.ss


def test_ss_inherited_checks():
    """Test that options are properly inherited.

    """
    class SSChecksParent2(SSChecksParent):

        ss = subsystem()

    assert SSChecksParent.ss is not SSChecksParent2.ss

    SSChecksParent2._test_ = True
    p = SSChecksParent2()
    assert p.ss.val == '1'
    assert p.ss.func() == 1

    p.clear_cache()
    SSChecksParent2._test_ = False
    with pytest.raises(I3pyFailedGet):
        p.ss.val
    with pytest.raises(I3pyFailedCall):
        p.ss.func()
