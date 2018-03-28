# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing the LazyPackage.

"""
import concurrent
from concurrent.futures import ThreadPoolExecutor
import pytest

from i3py.core.lazy_package import LazyPackage


def test_getting_a_local_value():
    """Test that we can access to local values.

    """
    pack = LazyPackage({}, 'test', '', {'a': 1})
    assert pack.a == 1
    assert sorted(pack.__all__) == ['a']


def test_doing_a_lazy_import():
    """Test that we can access to local values.

    """
    pack = LazyPackage({'ThreadPoolExecutor': 'futures.ThreadPoolExecutor'},
                       'test', '', {'a': 1})
    pack.__package__ = concurrent.__package__
    assert pack.ThreadPoolExecutor is ThreadPoolExecutor
    assert sorted(pack.__all__) == ['ThreadPoolExecutor', 'a']


def test_importing_from_another_lazy_package():
    """Test that we can access the namespace of another LazyPackage.

    """
    pack = LazyPackage({}, 'test', '',
                       {'test2': LazyPackage({'ThreadPoolExecutor':
                                              'futures.ThreadPoolExecutor'},
                                             'test', '', {'a': 1})})
    pack._local_vars['test2'].__package__ = concurrent.__package__
    assert pack.ThreadPoolExecutor is ThreadPoolExecutor
    assert sorted(pack.__all__) == ['ThreadPoolExecutor', 'a', 'test2']


def test_handling_missing_attr():
    """Test that we get the proper error in a meaningless case.

    """
    pack = LazyPackage({}, 'test', '',
                       {'test2': LazyPackage({'sqrt': 'math.sqrt'},
                                             'test', '', {'a': 1})})
    with pytest.raises(AttributeError):
        pack.b
