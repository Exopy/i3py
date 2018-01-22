# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Feature for scalars values which can only take discrete values.

"""
from .feature import Feature
from ..utils import validate_in


class Enumerable(Feature):
    """ Validate the set value against a finite set of allowed ones.

    Parameters
    ----------
    values : iterable, optional
        Permitted values for the property.

    """
    def __init__(self, getter=None, setter=None, values=(), extract='',
                 retries=0, checks=None, discard=None, options=None):
        super(Enumerable, self).__init__(getter, setter, extract, retries,
                                         checks, discard, options)
        self.values = set(values)
        self.creation_kwargs['values'] = values

        if values:
            self.modify_behavior('pre_set', self.validate_in.__func__,
                                 ('append',), 'validate',  True)

    def validate_in(self, driver, value):
        """Check the provided values is in the supported values.

        """
        return validate_in(driver, value, self.values, self.name)
