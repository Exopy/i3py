# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test basic metaclasses functionalities.

"""
from contextlib import ExitStack

from pytest import raises

from i3py.core.declarative import (subsystem, set_feat, channel, set_action,
                                   limit)
from i3py.core.composition import customize
from i3py.core.base_subsystem import SubSystem
from i3py.core.base_channel import Channel
from i3py.core.actions import Action
from i3py.core.features.feature import Feature
from i3py.core.errors import I3pyFailedGet, I3pyFailedCall

from .testing_tools import DummyParent


def test_documenting_feature():

    class DocTester(DummyParent):

        #: This is the docstring for
        #: the Feature test.
        test = Feature()

    assert DocTester.test.__doc__.split('\n')[0] ==\
        'This is the docstring for the Feature test.'


source =\
"""
class DocTester(DummyParent):

        #: This is the docstring for
        #: the Feature test.
        test = Feature()
"""


def test_unreachable_sources(caplog, monkeypatch):
    """Test defining a driver whose source cannot be retrieved for doc analysis

    """
    from i3py.core import has_features

    def false_getsourcelines(*args):
        raise OSError()

    monkeypatch.setattr(has_features, 'getsourcelines', false_getsourcelines)
    exec(source)
    assert caplog.records
    # If this execute we are good


def test_subclassing():
    """Ensure that when subclassing we clone all features/actions and name them

    """
    class ParentClass(DummyParent):

        f = Feature()

        @Action()
        def a():
            pass

    class Subclass(ParentClass):
        pass

    for f in ParentClass.__feats__:
        pf = getattr(ParentClass, f)
        sf = getattr(Subclass, f)
        assert pf is not sf
        assert pf.name == sf.name == f

    for a in ParentClass.__actions__:
        pa = getattr(ParentClass, a)
        sa = getattr(Subclass, a)
        assert pa is not sa
        assert pa.name == sa.name == a


# --- Test changing features defaults -----------------------------------------

def test_set_feat():
    """Test modifying a feature parameters using set_feat.

    """

    class DecorateIP(Feature):

        def __init__(self, getter=True, setter=True, retries=0,
                     extract=None, checks=None, discard=None, options=None,
                     dec='<br>'):
            super(DecorateIP, self).__init__(getter, setter)
            self.dec = dec

        def post_get(self, driver, value):
            return self.dec+value+self.dec

    class ParentTester(DummyParent):
        test = DecorateIP(getter=True, setter=True)

        @customize('test', 'get')
        def _get_test(feat, driver):
            return 'this is a test'

    class CustomizationTester(ParentTester):

        test = set_feat(dec='<it>')

    assert CustomizationTester.test is not ParentTester.test
    aux1 = ParentTester()
    aux2 = CustomizationTester()
    assert aux1.test != aux2.test
    assert aux2.test.startswith('<it>')
    assert ParentTester.test.name == 'test'
    assert CustomizationTester.test.name == 'test'


# --- Test overriding features behaviors --------------------------------------

def test_overriding_get():

    class NoOverrideGet(DummyParent):
        test = Feature(getter=True)

    assert NoOverrideGet().test

    class OverrideGet(DummyParent):
        test = Feature(getter=True)

        @customize('test', 'get')
        def _get_test(feat, driver):
            return 'This is a test'

    assert OverrideGet().test == 'This is a test'


def test_overriding_pre_get():

    class OverridePreGet(DummyParent):
        test = Feature(getter=True)

        @customize('test', 'get')
        def _get_test(feat, driver):
            return 'this is a test'

        @customize('test', 'pre_get')
        def _pre_get_test(feat, driver):
            assert False

    with raises(I3pyFailedGet):
        OverridePreGet().test


def test_overriding_post_get():

    class OverridePostGet(DummyParent):
        test = Feature(getter=True)

        @customize('test', 'get')
        def _get_test(feat, driver):
            return 'this is a test'

        @customize('test', 'post_get')
        def _post_get_test(feat, driver, value):
            return '<br>'+value+'<br>'

    assert OverridePostGet().test == '<br>this is a test<br>'


def test_overriding_set():

    class NoOverrideSet(DummyParent):
        test = Feature(setter=True)

    NoOverrideSet().test = 1

    class OverrideSet(DummyParent):
        test = Feature(setter=True)

        @customize('test', 'set')
        def _set_test(feat, driver, value):
            driver.val = value

    o = OverrideSet()
    o.test = 1
    assert o.val == 1


def test_overriding_pre_set():

    class OverridePreSet(DummyParent):
        test = Feature(setter=True)

        @customize('test', 'set')
        def _set_test(feat, driver, value):
            driver.val = value

        @customize('test', 'pre_set')
        def _pre_set_test(feat, driver, value):
            return value/2

    o = OverridePreSet()
    o.test = 1
    assert o.val == 0.5


def test_overriding_post_set():

    class OverridePreSet(DummyParent):
        test = Feature(setter=True)

        @customize('test', 'set')
        def _set_test(feat, driver, value):
            driver.val = value

        @customize('test', 'pre_set')
        def _pre_set_test(feat, driver, value):
            return value/2

        @customize('test', 'post_set')
        def _post_set_test(feat, driver, value, i_value, response):
            driver.val = (value, i_value)

    o = OverridePreSet()
    o.test = 1
    assert o.val == (1, 0.5)


def test_customizing_unknown():
    """Test customizing an undeclared feature.

    """

    with raises(AttributeError):

        class Overriding(DummyParent):

            @customize('test', 'get')
            def _get_test(feat, driver):
                return 1

# --- Test customizing feature ------------------------------------------------


class ToCustom(DummyParent):

    feat = Feature(getter=True, checks='driver.aux is True', )

    def __init__(self):
        super(ToCustom, self).__init__()
        self.aux = True
        self.aux2 = True
        self.custom_called = 0

    @customize('feat', 'get')
    def _get_feat(feat, driver):
        return feat


def test_customizing_append():

    class CustomAppend(ToCustom):

        @customize('feat', 'pre_get', ('append',))
        def _pre_get_feat(feat, driver):
            driver.custom_called += 1
            assert driver.aux2 is True

    driver = CustomAppend()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2


def test_customizing_prepend():

    class CustomPrepend(ToCustom):

        @customize('feat', 'pre_get', ('prepend',))
        def _pre_get_feat(feat, driver):
            driver.custom_called += 1
            assert driver.aux2 is True

    driver = CustomPrepend()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 3


def test_customizing_add_after():

    class CustomAddAfter(ToCustom):

        @customize('feat', 'pre_get', ('add_after', 'checks'))
        def _pre_get_feat(feat, driver):
            driver.custom_called += 1
            assert driver.aux2 is True

    driver = CustomAddAfter()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2


def test_customizing_add_before():

    class CustomAddBefore(ToCustom):

        @customize('feat', 'pre_get', ('add_before', 'checks'))
        def _pre_get_feat(feat, driver):
            driver.custom_called += 1
            assert driver.aux2 is True

    driver = CustomAddBefore()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 3


def test_customizing_replace():

    class CustomReplace(ToCustom):

        @customize('feat', 'pre_get', ('replace', 'checks'))
        def _pre_get_feat(feat, driver):
            driver.custom_called += 1
            assert driver.aux2 is True

    driver = CustomReplace()
    driver.aux = False
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2


class _CopyTest(ToCustom):
    """Class simply making sure that copying is not trivial.

    """
    @customize('feat', 'pre_get', ('append',), '_anch_')
    def _test(feat, driver):
        pass


class CopyTest(_CopyTest):
    """Class simply making sure that copying is not trivial.

    """
    @customize('feat', 'pre_get', ('prepend',), '_anch2_')
    def _test2(feat, driver):
        pass


class CopyTest2(_CopyTest):
    """Class simply making sure that copying is not trivial.

    """
    @customize('feat', 'pre_get', ('append',), '_anch2_')
    def _test2(feat, driver):
        pass


class CopyModfifcationTurnedToReplacement(ToCustom):
    """Class used to check that modification that were turned to replcament
    are properly copied

    """
    def __init__(self):
        super().__init__()
        self.counter = 0

    @customize('feat', 'post_get', ('append',), '_anch2_')
    def _test2(feat, driver, value):
        driver.counter += 1
        return value


def test_copying_custom_behvior():
    """Test copying a modification that was turned into a replacment.

    """
    class Subclass(CopyModfifcationTurnedToReplacement):
        pass

    # Chech the test class work
    c = CopyModfifcationTurnedToReplacement()
    assert c.counter == 0
    c.feat
    assert c.counter == 1

    # Check the subclass works
    s = Subclass()
    assert s.counter == 0
    s.feat
    assert s.counter == 1


def test_copying_custom_behavior1():
    """Test copying an appending.

    """

    class CustomAppend(CopyTest):

        @customize('feat', 'pre_get', ('append',))
        def _pre_get_feat(feat, driver):
            driver.custom_called += 1
            assert driver.aux2 is True

    class CopyingCustom(CustomAppend):

        feat = set_feat(checks=None)

    driver = CopyingCustom()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    driver.feat
    assert driver.custom_called == 3


def test_copying_custom_behavior2():
    """Test copying an add_after/add_before modification.

    """
    class CustomAddAfter(CopyTest):

        @customize('feat', 'pre_get', ('add_after', 'checks'))
        def _pre_get_feat(feat, driver):
            driver.custom_called += 1
            assert driver.aux2 is True

    class CustomAddAfter2(CopyTest2):

        @customize('feat', 'pre_get', ('add_after', 'checks'))
        def _pre_get_feat(feat, driver):
            driver.custom_called += 1
            assert driver.aux2 is True

    # Test handling a missing anchor
    class CopyingCustom(CustomAddAfter):

        feat = set_feat(checks=None)

    driver = CopyingCustom()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    driver.feat
    assert driver.custom_called == 3

    # Test handling a missing anchor and no other
    class CopyingCustom(CustomAddAfter2):

        feat = set_feat(checks=None)

    driver = CopyingCustom()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    driver.feat
    assert driver.custom_called == 3

    # Test handling a present anchor
    class CopyingCustomBis(CustomAddAfter):

        feat = set_feat()

    driver = CopyingCustomBis()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 1


def test_copying_custom_behavior3():
    """Test copying a replace behavior.

    """

    class CustomReplace(CopyTest):

        @customize('feat', 'pre_get', ('replace', 'checks'))
        def _pre_get_feat(feat, driver):
            driver.custom_called += 1
            assert driver.aux2 is True

    # Test handling a disappeared anchor
    class CopyingCustom(CustomReplace):

        feat = set_feat(checks=None)

    driver = CopyingCustom()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(I3pyFailedGet) as e:
        driver.feat
    assert isinstance(e.value.__cause__, AssertionError)
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    driver.feat
    assert driver.custom_called == 3


# --- Test customizing Action -------------------------------------------------

def test_set_action():
    """Test customizing an action using set_action.

    """
    class C1(DummyParent):

        @Action()
        def test(self, c):
            return c

    class C2(C1):

        test = set_action(values={'c': (1, 2)})

    assert C2.test is not C1.test
    assert not C1().test(0)
    assert C2().test(1)
    with raises(I3pyFailedCall) as einfo:
        C2().test(0)
    assert isinstance(einfo.value.__cause__, ValueError)
    assert C1.test.name == 'test'
    assert C2.test.name == 'test'


class WithAction(DummyParent):

    @Action()
    def test(self, c):
        return c


def test_customizing_action_pre_call():
    """Test customizing an action pre_call.

    """
    class PreCall(WithAction):

        @customize('test', 'pre_call')
        def _pre_call(action, driver, c):
            return (2*c,), {}

    assert PreCall().test(2) == 4

    class PreCall2(PreCall):

        @customize('test', 'pre_call', ('prepend',), 'custom2')
        def _pre_call2(action, driver, c):
            return (c**3,), {}

    assert PreCall2().test(2) == 16


def test_customizing_action_call():
    """Test customizing an Action call.

    """
    class Call(WithAction):

        @customize('test', 'call')
        def _call(action, driver, c):
            return 3*c

    assert Call().test(2) == 6


def test_customizing_action_post_call():
    """Test customizing an Action post_call.

    """
    class PostCall(WithAction):

        @customize('test', 'post_call')
        def _pre_call(action, driver, result, c):
            return result*c

    assert PostCall().test(3) == 9

    class PostCall2(PostCall):

        @customize('test', 'post_call', ('prepend',), 'custom2')
        def _post_call2(action, driver, result, c):
            return 3

    assert PostCall2().test(2) == 6


# --- Test declaring subsystems -----------------------------------------------


def test_subsystem_declaration1():
    """Test declaring a subsystem.

    """

    class DeclareSubsystem(DummyParent):

        #: Subsystem docstring
        sub_test = subsystem()

    assert DeclareSubsystem.sub_test.__doc__ == 'Subsystem docstring'
    d = DeclareSubsystem()
    assert d.__subsystems__
    assert type(d.sub_test) is DeclareSubsystem.sub_test
    assert isinstance(d.sub_test, SubSystem)


def test_subsystem_declaration2():
    """Test embedding a feature in a subsytem declaration.

    """

    class DeclareSubsystem2(DummyParent):

        #: Subsystem
        sub_test = subsystem()
        with sub_test as s:

            #: Subsystem feature doc
            s.test = Feature()

    assert isinstance(DeclareSubsystem2.sub_test.test, Feature)
    assert DeclareSubsystem2.sub_test.__doc__ == 'Subsystem'
    assert (DeclareSubsystem2.sub_test.test.__doc__.split('\n')[0] ==
            'Subsystem feature doc')
    d = DeclareSubsystem2()
    with raises(AttributeError):
        d.sub_test.test


def test_subsystem_declaration3():
    """Test embedding a method in a subsytem declaration.

    """

    class DeclareSubsystem3(DummyParent):

        sub_test = subsystem()
        with sub_test as s:
            s.test = Feature(getter=True)

            @s
            @customize('test', 'get')
            def _get_test(feat, driver):
                return True

    d = DeclareSubsystem3()
    assert d.sub_test.test


def test_subsystem_declaration4():
    """Test overriding a subsystem decl and specifying mixin class.

    """

    class DeclareSubsystem4(DummyParent):

        sub_test = subsystem()
        with sub_test as s:

            #: Subsystem feature doc
            s.aux = Feature()

    class Mixin(SubSystem):

        test = Feature(getter=True)

        @customize('test', 'get')
        def _get_test(feat, driver):
                return True

    class OverrideSubsystem(DeclareSubsystem4):

            sub_test = subsystem(Mixin)

    assert DeclareSubsystem4.sub_test.aux.__doc__

    d = OverrideSubsystem()
    assert d.sub_test.test
    assert d.sub_test.get_feat('aux').__doc__


def test_subsytem_declaration5():
    """Test nested subsytem declarations.

    """
    class DeclareSubsystem5(DummyParent):

        #: Subsystem docstring
        sub_test = subsystem()
        with sub_test as s:

            #: Nested subsystem
            s.sub = subsystem()

    assert DeclareSubsystem5.sub_test.sub.__doc__ == 'Nested subsystem'
    d = DeclareSubsystem5()
    assert d.sub_test.__subsystems__
    assert isinstance(d.sub_test.sub, SubSystem)


# --- Test declaring channels -----------------------------------------------

def test_channel_declaration1():
    """Test declaring a channel with a method returning the available ones.

    """

    class Dummy(Channel):
        pass

    class DeclareChannel(DummyParent):

        ch = channel('_available_ch', Dummy)

        def _available_ch(self):
            return (1,)

    d = DeclareChannel()
    assert d.__channels__
    assert d.ch is not DeclareChannel.ch
    assert d.ch.available == (1,)
    ch = d.ch[1]
    assert isinstance(ch, Dummy)
    assert d.ch[1] is ch


def test_channel_declaration2():
    """Test declaring a channel with a static set of channels and overriding it

    """

    class DeclareChannel(DummyParent):

        ch = channel((1,))

    class OverrideChannel(DeclareChannel):

        ch = channel()

        with ch:
            ch.test = Feature(getter=True)

            @ch
            @customize('test', 'get')
            def _get_test(self, driver):
                return 'This is a test'

    d = OverrideChannel()
    assert d.ch.available == (1,)
    assert d.ch[1].test == 'This is a test'


def test_channel_declaration3():
    """Test handling missing way to know available channels.

    """
    with raises(ValueError):
        class DeclareChannel(DummyParent):

            ch = channel()


def test_channel_declaration4():
    """Test declaring channel aliases.

    """

    class DeclareChannel(DummyParent):

        ch = channel((1, 2))

    class OverrideChannel(DeclareChannel):

        ch = channel(aliases={1: 'Test', 2: ('a', 'b')})

    class OverrideChannel2(OverrideChannel):

        ch = channel()

    d = OverrideChannel2()
    assert tuple(d.ch.available) == (1, 2)
    assert d.ch.aliases == {'Test': 1, 'a': 2, 'b': 2}
    assert d.ch['Test'].id == 1


# --- Test cache handling -----------------------------------------------------

class TestHasFeaturesCache(object):

    def setup(self):

        class CacheTest(DummyParent):
            test1 = Feature()
            test2 = Feature()

            ss = subsystem()
            with ss:
                ss.test = Feature()

            ch = channel('list_channels')
            with ch:
                ch.aux = Feature()

            def list_channels(self):
                return [1, 2]

        self.a = CacheTest()
        self.ss = self.a.ss
        self.ch1 = self.a.ch[1]
        self.ch2 = self.a.ch[2]

        self.a._cache = {'test1': 1, 'test2': 2}
        self.ss._cache = {'test': 1}
        self.ch1._cache = {'aux': 1}
        self.ch2._cache = {'aux': 2}

    def test_clear_all_caches(self):

        self.a.clear_cache()
        assert self.a._cache == {}
        assert self.ss._cache == {}
        assert self.ch1._cache == {}
        assert self.ch2._cache == {}

    def test_clear_save_ss(self):

        self.a.clear_cache(False)
        assert self.a._cache == {}
        assert self.ss._cache == {'test': 1}
        assert self.ch1._cache == {}
        assert self.ch2._cache == {}

    def test_clear_save_ch(self):

        self.a.clear_cache(channels=False)
        assert self.a._cache == {}
        assert self.ss._cache == {}
        assert self.ch1._cache == {'aux': 1}
        assert self.ch2._cache == {'aux': 2}

    def test_clear_by_feat(self):
        """Test clearinig only specified features cache.

        """

        self.a.clear_cache(features=['test1', 'ch.aux', 'ss.test'])
        assert self.a._cache == {'test2': 2}
        assert self.ss._cache == {}
        assert self.ch1._cache == {}
        assert self.ch2._cache == {}

    def test_check_cache_prop2(self):
        """Test clearing only specified features cache, using '.name' to access
        parent.

        """
        self.ss.clear_cache(features=['.test1', 'test', '.ch.aux'])
        assert self.a._cache == {'test2': 2}
        assert self.ss._cache == {}
        assert self.ch1._cache == {}
        assert self.ch2._cache == {}

    def test_check_cache_all_caches(self):
        res = self.a.check_cache()
        assert res == {'test1': 1, 'test2': 2, 'ss': {'test': 1},
                       'ch': {1: {'aux': 1}, 2: {'aux': 2}}}

    def test_check_cache_save_ss(self):
        res = self.a.check_cache(False)
        assert res == {'test1': 1, 'test2': 2,
                       'ch': {1: {'aux': 1}, 2: {'aux': 2}}}

    def test_check_cache_save_ch(self):
        res = self.a.check_cache(channels=False)
        assert res == {'test1': 1, 'test2': 2, 'ss': {'test': 1}}

    def test_check_cache_prop(self):
        """Test accessing only specified features cache.

        """
        res = self.a.check_cache(features=['test1', 'ss.test', 'ch.aux'])
        assert res == {'test1': 1, 'ss': {'test': 1},
                       'ch': {1: {'aux': 1}, 2: {'aux': 2}}}


# --- Test limits handling ----------------------------------------------------

def test_limits():

    class LimitsDecl(DummyParent):

        @limit('test')
        def _limits_test(self):
            return object()

        ss = subsystem()
        with ss:

            @ss
            @limit('test')
            def _ss_limits_test(self):
                return object()

        ch = channel((1, 2))
        with ch:

            @ch
            @limit('test')
            def _ch_limits_test(self):
                return object()

    class InheritedLimits(LimitsDecl):
        pass

    decl = InheritedLimits()
    lims = {}
    for obj in (decl, decl.ss, decl.ch[1], decl.ch[2]):
        assert set(obj.declared_limits) == set(['test'])
        r = obj.get_limits('test')
        assert obj.get_limits('test') is r
        lims[obj] = r

    decl.ss.discard_limits(('test', '.test', '.ch.test'))
    for obj in (decl, decl.ss, decl.ch[1], decl.ch[2]):
        assert decl.get_limits('test') is not lims[obj]


# --- Miscellaneous -----------------------------------------------------------

def test_get_feat():
    """Tes the get_feat method.

    """
    class Tester(DummyParent):

        #: This is the docstring for
        #: the Feature test.
        test = Feature()

    assert Tester().get_feat('test') is Tester.test


# --- Settings API ------------------------------------------------------------

def test_managing_settings():
    """Test getting, setting and temporarily setting settings.

    """
    c = ToCustom()
    assert c.read_settings('feat')['inter_set_delay'] == 0
    c.set_setting('feat', 'inter_set_delay', 1)
    assert c.read_settings('feat')['inter_set_delay'] == 1
    with raises(KeyError):
        c.set_setting('feat', '_last_set', 1)
    with raises(KeyError):
        c.set_setting('feat', 'xxxx', 1)

    with ExitStack() as stack:
        stack.enter_context(raises(RuntimeError))
        stack.enter_context(c.temporary_setting('feat', 'inter_set_delay', 0))
        assert c.read_settings('feat')['inter_set_delay'] == 0
        raise RuntimeError()

    assert c.read_settings('feat')['inter_set_delay'] == 1
