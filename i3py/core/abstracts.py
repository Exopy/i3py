# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Abstract classes used in I3py.

"""
from abc import ABCMeta, abstractmethod, abstractproperty

from abc import ABC


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
        """List the available channels (the aliases are not listed).

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


class AbstractSupportMethodCustomization(ABC):
    """Abstract class for objects supporting to have their method customized.

    """
    @abstractmethod
    def modify_behavior(self, method_name, func, specifiers=(),
                        internal=False):
        """Alter the behavior of the Feature using the provided method.

        Those operations are logged into the _customs dictionary in OrderedDict
        for each method so that they can be duplicated by copy_custom_behaviors
        The storing format is as follow : method, name of the operation, args
        of the operation.

        Parameters
        ----------
        method_name : unicode
            Name of the method which should be modified.

        func : callable|None
            Function to use when customizing the feature behavior, or None when
            removing a customization.

        specifiers : tuple, optional
            Tuple used to determine how the function should be used. If
            ommitted the function will simply replace the existing behavior
            otherwise it will be used to update the MethodComposer in the
            adequate fashion.
            The tuple content should be :
            - kind of modification : 'prepend', 'add_before', 'add_after',
              'append', replace', 'remove'
            - argument to the modifier, not necessary for prepend and append.
              It should refer to the id of a previous modification.
            ex : ('custom', 'add_after', 'old')

        modif_id : unicode
            Id of the modification, used to refer to it in later modification.
            It is this id that can be specified as target for 'add_before',
            'add_after', 'replace', remove'.

        internal : bool, optional
            Private flag used to indicate that this method is used for internal
            purposes and that the modification makes no sense to remember as
            this won't have to be copied by copy_custom_behaviors.

        """
        pass

    @abstractmethod
    def copy_custom_behaviors(self, obj):
        """Copy the custom behaviors existing on a feature to this one.

        This is used by set_feat to preserve the custom behaviors after
        recreating the feature with different kwargs. If an add_before or
        add_after clause cannot be satisfied because the anchor disappeared
        this method tries to insert the custom method in the most likely
        position.

        CAUTION : This method strives to build something that makes sense but
        it will most likely fail in some weird corner cases so avoid as mush as
        possible to use set_feat on feature modified using specially named
        method on the driver.

        """
        pass


class AbstractFeature(property, AbstractSupportMethodCustomization,
                      metaclass=ABCMeta):
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

    def clone(self):
        """Create a clone of itself.

        """
        new = type(self)(**self.creation_kwargs)
        new.copy_custom_behaviors(self)
        return new


class AbstractAction(AbstractSupportMethodCustomization):
    """Abstract base class for actions.

    Attributes
    ----------
    name : unicode
        Name under which this action is known in the class to which it
        belongs. This is set by the framework.

    creation_kwargs : dict
        Dictionary preserving the arguments with which the feature was
        initialized. This is used when customizing.

    func : callable
        Function on which the Action has been used as a decorator.

    """
    __slots__ = ('creation_kwargs', 'name', 'func')

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

    def clone(self):
        """Create a clone of itself.

        """
        new = type(self)(**self.creation_kwargs)
        new(self.func)
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


class AbstractGetSetFactory(ABC):
    """Abstract class for get/set factories.

    Use by Feature to identify such a factory and use it to replace the
    get/set method.

    """

    @abstractmethod
    def build_getter(self):
        """Build the function for getting the Feature value.

        This method is called when a get/set factory is passed as the getter
        argument to a Feature.

        """
        raise NotImplementedError()

    @abstractmethod
    def build_setter(self):
        """Build the function for setting the Feature value.

        This method is called when a get/set factory is passed as the setter
        argument to a Feature.

        """
        raise NotImplementedError()


class AbstractMethodCustomizer(ABC):
    """Abstract class for object used to specify a modification of a method.

    """
    @abstractmethod
    def __call__(self, func):
        """Use the method customizer as a decorator.

        """
        pass

    @abstractmethod
    def customize(self, owner, decorated_name):
        """Customize the object owned by owner.

        Parameters
        ----------
        owner : SupportMethodCustomization
            Class owning the descriptor to customize.

        decorate_name : unicode
            Name uder which the customization function appear in the class
            declaration.

        """
        pass
