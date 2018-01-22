# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Module dedicated to testing the Options feature.

"""
from pytest import raises

from i3py.core.features import Options


def test_handling_wrong_args():
    """Check that we do not accept
    """
    with raises(ValueError):
        Options(setter=True)
