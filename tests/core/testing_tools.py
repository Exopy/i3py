# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module defining some common tools for testing i3py.

"""
from threading import RLock

from i3py.core.has_features import HasFeatures


class DummyParent(HasFeatures):

    def __init__(self, caching_allowed=False):
        super(DummyParent, self).__init__(caching_allowed)
        self.d_get_called = 0
        self.d_get_cmd = None
        self.d_get_args = ()
        self.d_get_kwargs = {}
        self.d_get_raise = None
        self.d_set_called = 0
        self.d_set_cmd = None
        self.d_set_args = ()
        self.d_set_kwargs = {}
        self.d_set_raise = None
        self.d_check_instr = 0
        self.ropen_called = 0
        self.pass_check = True
        self.check_mess = ''
        self.lock = RLock()
        self.retries_exceptions = ()

    def default_get_feature(self, feat, cmd, *args, **kwargs):
        self.d_get_called += 1
        self.d_get_cmd = cmd
        self.d_get_args = args
        self.d_get_kwargs = kwargs
        if self.d_get_raise:
            raise self.d_get_raise()
        return cmd

    def default_set_feature(self, feat, cmd, *args, **kwargs):
        self.d_set_called += 1
        self.d_set_cmd = cmd
        self.d_set_args = args
        self.d_set_kwargs = kwargs
        if self.d_set_raise:
            raise self.d_set_raise()

    def default_check_operation(self, feat, value, i_value, response):
        self.d_check_instr += 1
        if self.pass_check:
            return True, None
        else:
            return False, self.check_mess

    def reopen_connection(self):
        self.ropen_called += 1
