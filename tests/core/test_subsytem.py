# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test basic subsystem instance functionalities.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from i3py.core.has_features import subsystem
from i3py.core.base_subsystem import SubSystem
from .testing_tools import DummyParent


def test_declaration_meta():

    assert SubSystem() is SubSystem


class SSParent(DummyParent):

    ss = subsystem()


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
