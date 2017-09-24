# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tests for the base class Feature capabilities.

"""
from pytest import raises
from stringparser import Parser

from i3py.core.composition import customize
from i3py.core.declarative import limit
from i3py.core.features.feature import Feature, get_chain, set_chain
from i3py.core.features.factories import constant, conditional
from i3py.core.errors import I3pyError, I3pyFailedGet, I3pyFailedSet
from ..testing_tools import DummyParent


class TestFeatureInit(object):
    """Test that all init parameters are correctly stored.

    This class can easily be extended to other feature by overriding the
    parameters class attribute with the added keywords, and the cls attribute.

    """
    cls = Feature

    defaults = dict(getter=True, setter=True)

    parameters = dict(extract='{}',
                      retries=1,
                      checks='1>0',
                      discard={'limits': 'test'}
                      )

    exclude = list()

    def test_init(self):

        e = []
        for c in type.mro(type(self)):
            if c is not object:
                e.extend(c.exclude)
        p = {}
        d = {}
        for c in type.mro(type(self)):
            if c is not object:
                p.update(c.parameters)
                d.update(c.defaults)

        for k, v in p.items():
            if k not in e:
                kwargs = d.copy()
                kwargs[k] = v
                feat = self.cls(**kwargs)
                assert feat.creation_kwargs[k] == v


def test_standard_post_set():
    """Test the standard post_set method relying on the driver checks.

    """
    feat = Feature()
    driver = DummyParent()

    feat.post_set(driver, 1, 1.0, None)
    assert driver.d_check_instr == 1

    with raises(I3pyError):
        driver.pass_check = False
        feat.post_set(driver, 1, 1.0, None)

    with raises(I3pyError):
        driver.check_mess = 'Error'
        feat.post_set(driver, 1, 1.0, None)


def test_multiple_set():
    """Test multiple repeated setting of the same value.

    """
    class SetTester(DummyParent):

        feat = Feature(setter='set {}')

    driver = SetTester(True)
    driver.feat = 1
    assert driver.d_set_called == 1
    driver.feat = 1
    assert driver.d_set_called == 1


def test_del():
    """Test deleting a feature does clear the cache.

    """
    class SetTester(DummyParent):

        feat = Feature(setter='set {}')

    driver = SetTester(True)
    driver.feat = 1
    assert driver.d_set_called == 1
    del driver.feat
    driver.feat = 1
    assert driver.d_set_called == 2


def test_getter_factory():
    """Test using a getter factory.

    """
    class FactoryTester(DummyParent):

        feat = Feature(constant('Test'))

    driver = FactoryTester()
    assert driver.feat == 'Test'


def test_setter_factory():
    """Test using a factory setter.

    """
    class FactoryTester(DummyParent):

        state = False

        feat = Feature(setter=conditional('1 if driver.state else 2', True))

    driver = FactoryTester()
    driver.feat = None
    assert driver.d_set_cmd == 2
    driver.state = True
    driver.feat = True
    assert driver.d_set_cmd == 1


def test_get_chain():
    """Test the get_chain capacity to iterate in case of driver issue.

    """
    driver = DummyParent()
    driver.retries_exceptions = (I3pyError,)
    driver.d_get_raise = I3pyError

    feat = Feature(True, retries=1)

    with raises(I3pyError):
        get_chain(feat, driver)

    assert driver.d_get_called == 2


def test_set_chain():
    """Test the set_chain capacity to iterate in case of driver issue.

    """
    driver = DummyParent()
    driver.retries_exceptions = (I3pyError,)
    driver.d_set_raise = I3pyError

    feat = Feature(setter=True, retries=1)

    with raises(I3pyError):
        set_chain(feat, driver, 1)

    assert driver.d_set_called == 2


def test_discard_cache():
    """Test discarding the cache associated with a feature.

    """

    class Cache(DummyParent):

        val = 1

        feat_cac = Feature(getter=True)
        feat_dis = Feature(setter=True, discard=('feat_cac',))

        @customize('feat_cac', 'get')
        def _get_feat_cac(feat, driver):
            return driver.val

        @customize('feat_dis', 'set')
        def _set_feat_dis(feat, driver, value):
            driver.val = value

    driver = Cache(True)
    assert driver.feat_cac == 1
    driver.val = 2
    assert driver.feat_cac == 1
    driver.feat_dis = 3
    assert driver.feat_cac == 3


def test_discard_cache2():
    """Test discarding the cache of both features and limits.

    """

    class Cache(DummyParent):

        val = 1
        li = 1

        feat_cac = Feature(getter=True)
        feat_dis = Feature(setter=True, discard={'features': ('feat_cac',),
                                                 'limits': ('lim', )})

        @customize('feat_cac', 'get')
        def _get_feat_cac(feat, driver):
            return driver.val

        @customize('feat_dis', 'set')
        def _set_feat_dis(feat, driver, value):
            driver.val = value

        @limit('lim')
        def _limits_lim(self):
            self.li += 1
            return self.li

    driver = Cache(True)
    assert driver.feat_cac == 1
    assert driver.get_limits('lim') == 2
    driver.val = 2
    assert driver.feat_cac == 1
    assert driver.get_limits('lim') == 2
    driver.feat_dis = 3
    assert driver.feat_cac == 3
    assert driver.get_limits('lim') == 3


def test_discard_cache3():
    """Test discarding the cache of limits only.

    """

    class Cache(DummyParent):

        val = 1
        li = 1

        feat_dis = Feature(setter=True, discard={'limits': ('lim', )})

        @customize('feat_dis', 'set')
        def _set_feat_dis(feat, driver, value):
            driver.val = value

        @limit('lim')
        def _limits_lim(self):
            self.li += 1
            return self.li

    driver = Cache(True)
    assert driver.get_limits('lim') == 2
    driver.val = 2
    assert driver.get_limits('lim') == 2
    driver.feat_dis = 3
    assert driver.get_limits('lim') == 3


def test_feature_checkers():
    """Test use of checks keyword in Feature.

    """

    class AuxParent(DummyParent):

        aux = 1
        feat = Feature(True)
        feat_ch = Feature(True, True,
                          checks='driver.aux==1; driver.feat is True')
        feat_gch = Feature(True, True, checks=('driver.aux==1', None))
        feat_sch = Feature(True, True, checks=(None, 'driver.aux==1'))

    assert hasattr(AuxParent.feat_ch, 'get_check')
    assert hasattr(AuxParent.feat_ch, 'set_check')
    assert hasattr(AuxParent.feat_gch, 'get_check')
    assert not hasattr(AuxParent.feat_gch, 'set_check')
    assert not hasattr(AuxParent.feat_sch, 'get_check')
    assert hasattr(AuxParent.feat_sch, 'set_check')

    driver = AuxParent()
    driver.feat_ch
    driver.feat_gch
    driver.feat_sch
    driver.feat_ch = 1
    driver.feat_gch = 1
    driver.feat_sch = 1

    driver.aux = False
    with raises(I3pyFailedGet) as e:
        driver.feat_ch
        assert isinstance(e.__cause__, AssertionError)
    with raises(I3pyFailedGet):
        driver.feat_gch
        assert isinstance(e.__cause__, AssertionError)
    driver.feat_sch
    with raises(I3pyFailedSet):
        driver.feat_ch = 1
        assert isinstance(e.__cause__, AssertionError)
    driver.feat_gch = 1
    with raises(I3pyFailedSet):
        driver.feat_sch = 1
        assert isinstance(e.__cause__, AssertionError)


def test_clone():
    """Test cloning a feature.

    """

    feat_ch = Feature(True, True, checks='driver.aux==1; driver.feat is True')
    new = feat_ch.clone()
    assert feat_ch.pre_get is not new.pre_get
    assert feat_ch._customs is not new._customs


def test_analyse_function():
    """Test analysing a function used to customize a method.

    """
    feat = Feature()
    func = lambda feat, driver, value: value

    # Test handling specifiers for get/set
    for target in ('get', 'set'):
        with raises(ValueError):
            feat.analyse_function(target, func, (None,))

    # Test handling wrong signature
    with raises(ValueError):
        feat.analyse_function('pre_get', func, ())


def test_modify_behavior1():
    """Modify by replacing by a stand-alone method

    """
    feat = Feature()
    func = lambda feat, driver, value: value
    feat.modify_behavior('post_get', func)
    assert feat.post_get.__func__ is func
    assert feat._customs['post_get'] is func


def test_modify_behavior2():
    """Modify a method that has not yet a MethodsComposer.

    """
    feat = Feature()

    def meth(feat, driver, value):
        return value
    feat.modify_behavior('post_get', meth, ('append',), 't')
    feat.modify_behavior('post_get', meth, ('append',))
    assert 'custom' in feat._customs['post_get']
    assert feat._customs['post_get']['custom'][1] == ('append',)
    assert (feat._customs['post_get']['custom'][0] == meth)


def test_modify_behavior3():
    """Test all possible cases of behaviour modifications.

    """
    test = Feature(True, True)

    # Test replacing a method.
    test.modify_behavior('get', lambda feat, driver: 1)
    assert test.get(None) == 1

    def r(feat, driver):
        raise ValueError()

    test.modify_behavior('pre_get', r)
    with raises(ValueError):
        test.pre_get(None)

    # Test modifying and already customized method.
    def r2(feat, driver):
        raise KeyError()

    test.modify_behavior('pre_get', r2, ('prepend',), 'custom')
    with raises(KeyError):
        test.pre_get(None)

    test.modify_behavior('pre_get', None, ('remove', 'custom'))
    with raises(ValueError):
        test.pre_get(None)

    test.modify_behavior('pre_get', r2, ('add_before', 'old'), 'custom')
    with raises(KeyError):
        test.pre_get(None)

    test.modify_behavior('pre_get', lambda feat, driver: 1,
                         ('replace', 'custom'), 'custom')
    with raises(ValueError):
        test.pre_get(None)

    # Test replacing and internal customization.
    def r(feat, driver, value):
        raise ValueError()

    def r2(feat, driver, value):
        raise KeyError()

    test.modify_behavior('post_get', r, ('prepend',), 'test1', True)
    test.modify_behavior('post_get', r2, ('append',), 'test2', True)

    test.modify_behavior('post_get', lambda feat, driver, value: 1,
                         ('replace', 'test1'), 'test1')
    with raises(KeyError):
        test.post_get(None, 0)

    test.modify_behavior('post_get', r, ('replace', 'test2'), 'test2')
    with raises(ValueError):
        test.post_get(None, 0)


def test_copy_custom_behaviors():
    """Test copy customs behaviors.

    """
    def r2(feat, driver, value):
        raise KeyError()

    modified_feature = Feature(True, True, checks='1 < 2', extract='{}')
    mb = modified_feature.modify_behavior
    mb('get', lambda feat, driver: 1)
    mb('pre_get', lambda feat, driver: 1, ('add_before', 'checks'), 'custom')
    mb('post_get', lambda feat, driver, value: 2*value,
       ('add_after', 'extract'), 'custom')
    mb('pre_set', lambda feat, driver, value: 1, ('prepend',), 'aux')
    mb('pre_set', lambda feat, driver, value: 1, ('append',), 'aux2')
    mb('pre_set', r2, ('add_after', 'checks'), 'custom')
    mb('post_set', lambda feat, driver, value, i_value, response: 1,
       ('prepend',), 'aux', True)
    mb('post_set', lambda feat, driver, value, i_value, response: 1,
       ('add_after', 'aux'), 'custom')

    feat = Feature(True, True, extract='{}')
    feat.modify_behavior('pre_set', lambda feat, driver, value: 1,
                         ('append',), 'test')
    feat.modify_behavior('pre_get', lambda feat, driver: 1, ('append',),
                         'test')
    feat.copy_custom_behaviors(modified_feature)

    assert feat.get(None) == 1
    with raises(KeyError):
        feat.pre_set(None, 1)

    # Already covered in test_has_features but should be here
    # TODO add test for existing anchor
    # TODO add for missing anchor leading to either append or prepend


def test_extract():
    """Test extracting a value, when extract is a string.

    """

    feat = Feature(extract='The value is {:d}')
    val = feat.post_get(None, 'The value is 11')
    assert val == 11

    feat = Feature(extract=Parser('The value is {:d}'))
    val = feat.post_get(None, 'The value is 11')
    assert val == 11

# Other behaviors are tested by the tests in test_has_features.py
