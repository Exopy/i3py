# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Abstract classes used in I3py.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from abc import ABC, ABCMeta, abstractmethod, abstractproperty

from future.utils import with_metaclass


class AbstractHasFeatures(ABC):
    """Sentinel class for the collections of Features.

    """
    pass


class AbstractSubSystem(ABC):
    """Sentinel for subsystem identification.

    """
    pass

AbstractHasFeatures.register(AbstractSubSystem)


class AbstractChannel(ABC):
    """Sentinel class for channel identification.

    """
    pass

AbstractHasFeatures.register(AbstractChannel)


class AbstractChannelContainer(ABC):
    """Abstract container class for instrument channels.

    The interface is defined in the ChannelContainer subclass.

    """
    @abstractproperty
    def available(self):
        """List the available channels.

        """
        pass

    @abstractproperty
    def aliases(self):
        """List the aliases.

        """
        pass

    @abstractproperty
    def __getitem__(self, ch_id):
        pass

    def __iter__(self):
        for id in self.available:
            yield self[id]


class AbstractFeature(with_metaclass(ABCMeta, property)):
    """Abstract class for Features.

    Attributes
    ----------
    name : unicode
        Name under which this feature is known in the class to which it
        belongs. This is set by the framework.

    creation_kwargs : dict
        Dictionary preserving the arguments with which the feature was
        initialized. This is used when customizing.

    """
    __slots__ = ('creation_kwargs', 'name')

    @abstractmethod
    def make_doc(self, doc):
        """Build a comprehensive docstring from the provided user doc and using
        the configuration of the feature.

        """
        pass

    @abstractmethod
    def copy_custom_behaviors(self, feat):
        """Copy the customized behavior of another feature.

        """
        # XXX describe customized behavior
        pass

    def clone(self):
        """Create a clone of itself.

        """
        new = type(self)(**self.creation_kwargs)
        new.copy_custom_behaviors(self)
        return new


class AbstractAction(ABC):
    """Abstract base class for actions.

    """
    __slots__ = ('creation_kwargs', 'name')

    @abstractmethod
    def __call__(self, func):
        """Invoked when the class is used as a decorator.

        """
        pass

    @abstractmethod
    def __get__(self, obj, objtype=None):
        """Descriptor protocol.

        Should return a callable.

        """
        pass

    @abstractmethod
    def copy_custom_behaviors(self, feat):
        """Copy the customized behavior of another feature.

        """
        # XXX describe customized behavior
        pass

    def clone(self):
        """Create a clone of itself.

        """
        new = type(self)(**self.creation_kwargs)
        new.copy_custom_behaviors(self)
        return new


class AbstractLimitsValidator(ABC):
    """ Base class for all limits validators.

    Attributes
    ----------
    minimum :
        Minimal allowed value or None.
    maximum :
        Maximal allowed value or None.
    step :
        Allowed step between values or None.

    Methods
    -------
    validate :
        Validate a given value against the range.

    """
    __slots__ = ('minimum', 'maximum', 'step', 'validate')
