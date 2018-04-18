# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test the use of the declarative class building helpers.

"""
from collections import OrderedDict
import pytest

from i3py.core.features import Feature
from i3py.core.actions import Action
from i3py.core.declarative import (subsystem, channel, set_feat, set_action,
                                   limit, SUBPART_FUNC)


@pytest.fixture
def subpart_decl():
    """Subbpart declaration used for testing.

    """
    return subsystem()


def test_subpart_decl_setattr(subpart_decl):
    """Test setting an attribute.

    For other child subpart declaration the _parent_ attribute is set at this
    step.

    """
    subpart_decl.a = 1
    assert subpart_decl.a == 1
    subpart_decl.ss = subsystem()
    assert subpart_decl.ss._parent_ is subpart_decl


def test_subpart_decl_call(subpart_decl):
    """Test using a subpart decl as decorator.

    """
    def test_method(self):
        return 1

    assert subpart_decl(test_method) is SUBPART_FUNC
    assert subpart_decl.test_method is test_method


def test_subpart_decl_context(subpart_decl):
    """Test that when used as a context manager the frame is properly cleaned.

    Also check the collection of aliases.

    """
    with subpart_decl as ss:
        ss.a = 1

        @ss
        def test(self):
            pass

        b = 1
        ss.c = b

    assert subpart_decl.a
    assert subpart_decl.test and 'test' in subpart_decl._inners_
    assert subpart_decl.c and 'b'in subpart_decl._inners_
    assert 'ss' in subpart_decl._aliases_

    # Check cleaning locals from inner values.
    class Container:
        pass

    for k, v in locals().items():
        setattr(Container, k, v)
    subpart_decl.clean_namespace(Container)
    for n in ('ss', 'test', 'b'):
        assert n not in Container.__dict__

    # Check that identity test prevent from cleaning overwritten values
    b = 2

    class Container:
        pass

    for k, v in locals().items():
        setattr(Container, k, v)
    subpart_decl.clean_namespace(Container)
    assert 'b' in Container.__dict__


def test_subpart_decl_build_cls(subpart_decl):
    """Test that the class creation does get the docs and set the attributes.

    """
    class Test:
        pass

    with subpart_decl as ss:
        ss.a = Feature()

    subpart_decl._name_ = 'sub'
    cls = subpart_decl.build_cls(Test, None, {'sub': 'Test docs',
                                              'ss.a': 'A docs'})
    assert cls.__doc__ == 'Test docs'
    assert cls.__name__ == 'TestSub'
    assert not hasattr(cls, '_docs_')
    assert cls.a.__doc__.split('\n')[0] == 'A docs'
    assert cls
    for att in ('_name_', '_parent_', '_bases_', '_aliases_'):
        assert not hasattr(cls, att)

    class T:
        pass

    cls2 = subpart_decl.build_cls(T, cls, {})
    assert cls2.__name__ == 'TSub'
    assert cls2.mro()[1] is cls


def test_subsystem_decl_base_cls():
    """Test computing the base classes for a subsystem.

    """
    ss = subsystem()
    bases = ss.compute_base_classes()
    from i3py.core.base_subsystem import SubSystem
    assert bases[0] is SubSystem

    ss._bases_ = [SubSystem]
    bases = ss.compute_base_classes()
    assert bases[0] is SubSystem and len(bases) == 1


def test_channel_decl_base_cls():
    """Test computing the base classes for a channel.

    """
    ch = channel()
    bases = ch.compute_base_classes()
    from i3py.core.base_channel import Channel
    assert bases[0] is Channel

    ch._bases_ = [Channel]
    bases = ch.compute_base_classes()
    assert bases[0] is Channel and len(bases) == 1


def test_channel_decl_list_channel_func():
    """Test building the channel listing function.

    """
    ch = channel((1, 2, 3))
    list_func = ch.build_list_channel_function()
    assert list_func(None) == (1, 2, 3)

    class FalseDriver(object):

        @classmethod
        def att(cls):
            return (4, 5)

    ch = channel('att')
    list_func = ch.build_list_channel_function()
    assert list_func(FalseDriver) == (4, 5)


def test_set_feat_customize():
    """Test customizing a Feature.

    """
    f = Feature(getter=True, checks='driver.enabled')

    def custom_pre_get(feat, driver):
        return 1

    f._customs['pre_get'] = OrderedDict()
    f._customs['pre_get']['custom'] = (custom_pre_get, ('prepend',))

    sf = set_feat(checks='driver.disabled')
    new = sf.customize(f)
    assert f.creation_kwargs['checks'] == 'driver.enabled'
    assert new.creation_kwargs['checks'] == 'driver.disabled'
    assert new._customs == f._customs


def test_set_action_customize():
    """Test customizing an Action.

    """
    a = Action(checks='driver.enabled')

    @a
    def func(self, *args, **kwargs):
        pass

    def custom_pre_call(action, driver, *args, **kwargs):
        return 1

    a._customs['pre_call'] = OrderedDict()
    a._customs['pre_call']['custom'] = (custom_pre_call, ('prepend',))

    sa = set_action(checks='driver.disabled')
    new = sa.customize(a)
    assert a.creation_kwargs['checks'] == 'driver.enabled'
    assert new.creation_kwargs['checks'] == 'driver.disabled'
    assert new._customs == a._customs
    assert new.func is a.func


def test_limit_extract_id():
    """Test decorating a limit function.

    """
    l = limit('voltage')

    def func(self):
        pass

    assert l.name == 'voltage'
    assert l(func).func is func


def test_limit_in_subsystem(subpart_decl):
    """Test decorating a limit function in a subsystem.

    """
    class Test:
        pass

    with subpart_decl as ss:
        ss.a = 1

        @ss
        @limit('voltage')
        def test(self):
            pass

    assert subpart_decl.test.name == 'voltage'
    cls = subpart_decl.build_cls(Test, None, {'sub': 'Test docs',
                                              'ss.a': 'A docs'})
    assert 'voltage' in cls.__limits__
