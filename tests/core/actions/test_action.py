# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing action behavior.

"""
from pytest import mark, raises

from i3py.core import limit, customize, subsystem
from i3py.core.actions import Action
from i3py.core.limits import IntLimitsValidator
from i3py.core.unit import UNIT_SUPPORT, get_unit_registry
from i3py.core.errors import I3pyFailedCall
from i3py.core.features import Options
from ..testing_tools import DummyParent, DummyDriver


def test_naked_action():
    """Test defining a simple action.

    """
    class Dummy(DummyParent):

        @Action()
        def test(self):
            return type(self)

    assert isinstance(Dummy.test, Action)

    dummy = Dummy()
    assert dummy.test() is Dummy


def test_erroring_action():
    """Ensure that an action erroring generate a readable traceback.

    """
    class Dummy(DummyParent):

        @Action()
        def test(self):
            raise RuntimeError()

    dummy = Dummy()
    with raises(I3pyFailedCall) as e:
        dummy.test()

    print(e.getrepr())
    assert str(e.getrepr()).strip().startswith('def __call__')


def test_handling_double_decoration():
    """Test attempting to decorate twice using a single Action.

    """
    class Dummy(DummyParent):

        @Action()
        def test(self):
            return type(self)

    with raises(RuntimeError):
        Dummy.test(lambda x: x)


def test_retries_support():
    """Test the get_chain capacity to iterate in case of driver issue.

    """
    class Dummy(DummyParent):

        called = 0
        retries_exceptions = (RuntimeError,)

        @Action(retries=1)
        def test(self):
            print(self.retries_exceptions)
            Dummy.called += 1
            raise RuntimeError()

    dummy = Dummy()
    with raises(I3pyFailedCall) as e:
        dummy.test()

    assert str(e.getrepr()).strip().startswith('def __call__')
    assert Dummy.called == 2


def test_options_action():
    """Test handling options in an Action definition.

    """
    class Dummy(DummyDriver):

        _test_ = True

        op = Options(names={'test': None})

        @customize('op', 'get')
        def _get(feat, driver):
            return {'test': driver._test_}

        sub = subsystem()

        with sub as ss:

            @ss
            @Action(options='op["test"]')
            def test(self):
                return type(self)

    a = Dummy()
    assert a.sub.test

    Dummy._test_ = False
    b = Dummy()
    with raises(AttributeError):
        b.sub.test


def test_values_action():
    """Test defining an action with values validation.

    """
    class Dummy(DummyParent):

        @Action(values={'a': (1, 2, 3)})
        def test(self, a, b):
            return a * b

    dummy = Dummy()
    assert dummy.test(1, 5) == 5
    with raises(I3pyFailedCall) as e:
        dummy.test(5, 2)
        assert isinstance(e.__cause__, ValueError)


def test_limits_action1():
    """Test defining an action with integer limits validation.

    """
    class Dummy(DummyParent):

        @Action(limits={'b': (1, 10, 2)})
        def test(self, a, b):
            return a

    dummy = Dummy()
    assert dummy.test(1, 1) == 1
    with raises(I3pyFailedCall) as e:
        dummy.test(2,  2)
        assert isinstance(e.__cause__, ValueError)


def test_limits_action2():
    """Test defining an action with floating limits validation.

    """
    class Dummy(DummyParent):

        @Action(limits={'b': (1.0, 10.0, 0.1)})
        def test(self, a, b):
            return a

    dummy = Dummy()
    assert dummy.test(1, 1)
    with raises(I3pyFailedCall) as e:
        dummy.test(2,  1.05)
        assert isinstance(e.__cause__, ValueError)


def test_limits_action3():
    """Test defining an action getting the limits from the driver.

    """
    class Dummy(DummyParent):

        @Action(limits={'b': 'c'})
        def test(self, a, b):
            return a

        @limit('c')
        def _limits_c(self):
            return IntLimitsValidator(1, 10, 2)

    dummy = Dummy()
    assert dummy.test(1, 1)
    with raises(I3pyFailedCall) as e:
        dummy.test(2,  2)
        assert isinstance(e.__cause__, ValueError)


def test_limits_action4():
    """Test defining an action with the wrong type of limits.

    """
    with raises(TypeError):
        class Dummy(DummyParent):

            @Action(limits={'b': 1})
            def test(self, a, b):
                return a


def test_action_with_overlapping_limits_and_values():
    """Test defining an action validating the same parameter using values and
    limits.

    """
    with raises(ValueError):
        class Dummy(DummyParent):

            @Action(limits={'b': (1, 10, 2)}, values={'b': (1, 2, 3)})
            def test(self, a, b):
                return a


@mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
def test_action_with_unit():
    """Test defining an action using units conversions.

    """
    class Dummy(DummyParent):

        @Action(units=('ohm*A', (None, 'ohm', 'A')))
        def test(self, r, i):
            return r*i

    assert isinstance(Dummy.test, Action)

    dummy = Dummy()
    ureg = get_unit_registry()
    assert dummy.test(2, ureg.parse_expression('3000 mA')) ==\
        ureg.parse_expression('6 V')

    # Ensure that we respect the default for the setting as defined by
    # UNIT_RETURn.
    from i3py.core.actions import action

    try:
        action.UNIT_RETURN = False

        class Dummy(DummyParent):

            @Action(units=('ohm*A', (None, 'ohm', 'A')))
            def test(self, r, i):
                return r*i

        dummy = Dummy()

    finally:
        action.UNIT_RETURN = True

    assert dummy.test(2, 3) == 6

    # Ensure we respect the dynamically set setting.
    with dummy.temporary_setting('test', 'unit_return', True):
        assert dummy.test(2, ureg.parse_expression('3000 mA')) ==\
            ureg.parse_expression('6 V')

    with raises(ValueError):

        class Dummy(DummyParent):

            @Action(units=('ohm*A', ('ohm', 'A')))
            def test(self, r, i):
                return r*i


def test_action_with_checks():
    """Test defining an action with checks.

    """
    class Dummy(DummyParent):

        @Action(checks='r>i;i>0')
        def test(self, r, i):
            return r*i

    assert isinstance(Dummy.test, Action)

    dummy = Dummy()
    assert dummy.test(3, 2) == 6
    with raises(I3pyFailedCall) as e:
        dummy.test(2, 2)
    assert isinstance(e.value.__cause__, AssertionError)

    with raises(I3pyFailedCall) as e:
        dummy.test(3, -1)
    assert isinstance(e.value.__cause__, AssertionError)


def test_analyse_function():
    """Test analysing a function proposed to customize a method.

    """
    # Call case
    # - ok : expected signature
    # - specifiers found
    # - wrong signature
    act = Action()
    act(lambda driver, val: 1)
    specs, sigs, chain_on =\
        act.analyse_function('call', lambda action, driver, val: 2, ())
    assert not specs and chain_on is None
    assert sigs == [('action', 'driver', 'val')]
    with raises(ValueError) as e:
        act.analyse_function('call', lambda action, driver, val: 2,
                             ('append',))
    assert 'Can only replace' in e.exconly()
    with raises(ValueError) as e:
        act.analyse_function('call', lambda action, driver: 2, ())
    assert 'Function' in e.exconly()

    # Pre-call case
    # - ok : expected signature (clean specifiers)
    # - ok : generic signature (keep specifiers)
    # - wrong signature
    pc = lambda action, driver, val: val*2
    specs, sigs, chain_on =\
        act.analyse_function('pre_call', pc, ('append',))
    assert not specs and chain_on == 'args, kwargs'
    assert sigs == [('action', 'driver', '*args', '**kwargs'),
                    ('action', 'driver', 'val')]
    act.modify_behavior('pre_call', pc)
    specs, sigs, chain_on =\
        act.analyse_function('pre_call',
                             lambda action, driver, *args, **kwargs:
                                 (args, kwargs),
                             ('add_before', 'custom'))
    assert specs == ('add_before', 'custom')
    assert chain_on == 'args, kwargs'
    assert sigs == [('action', 'driver', '*args', '**kwargs'),
                    ('action', 'driver', 'val')]
    with raises(ValueError) as e:
        act.analyse_function('pre_call', lambda action, driver: 2, ())
    assert 'Function' in e.exconly()

    # Post-call case
    # - ok : expected signature (keep specifiers)
    # - ok : generic signature (clean specifiers)
    # - wrong signature
    pc = lambda action, driver, result, val: result*2
    specs, sigs, chain_on =\
        act.analyse_function('post_call', pc, ('append',))
    assert not specs and chain_on == 'result'
    assert sigs == [('action', 'driver', 'result', '*args', '**kwargs'),
                    ('action', 'driver', 'result', 'val')]
    act.modify_behavior('post_call', pc)
    specs, sigs, chain_on =\
        act.analyse_function('post_call',
                             lambda action, driver, result, *args, **kwargs:
                                 result,
                             ('add_before', 'custom'))
    assert specs == ('add_before', 'custom')
    assert chain_on == 'result'
    assert sigs == [('action', 'driver', 'result', '*args', '**kwargs'),
                    ('action', 'driver', 'result', 'val')]
    with raises(ValueError) as e:
        act.analyse_function('post_call', lambda action, driver: 2, ())
    assert 'Function' in e.exconly()

    # Wrong method name
    with raises(ValueError) as e:
        act.analyse_function('test', lambda x: 1, ())
    assert 'Cannot customize method' in e.exconly()
