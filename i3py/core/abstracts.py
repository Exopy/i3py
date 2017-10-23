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
from abc import ABC, abstractmethod, abstractproperty


class AbstractHasFeatures(ABC):
    """Sentinel class for the collections of Features.

    """
    # XXX document
    #:
    __feats__ = {}

    #:
    __actions__ = {}

    #:
    __subsystems__ = {}

    #:
    __channels__ = {}

    #:
    __limits__ = {}


class AbstractBaseDriver(ABC):
    """Sentinel class for the identification of a driver.

    """
    pass


class AbstractSubSystem(ABC):
    """Sentinel for subsystem identification.

    """
    pass


AbstractHasFeatures.register(AbstractSubSystem)


class AbstractSubSystemDescriptor(property, ABC):
    """Abstract subsystem descriptor.

    """
    pass


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
    def available(self) -> list:
        """List the available channels (the aliases are not listed).

        """
        pass

    @abstractproperty
    def aliases(self) -> list:
        """List the aliases.

        """
        pass

    @abstractproperty
    def __getitem__(self, ch_id):
        pass

    @abstractmethod
    def __iter__(self):
        pass


class AbstractChannelDescriptor(property, ABC):
    """Abstract subsystem descriptor.

    """
    pass


class AbstractSubpartDeclarator(ABC):
    """Sentinel for subpart declaration in a class body.

    See declarative.SubpartDecl for the interface definition.

    """
    pass


class AbstractSubSystemDeclarator(AbstractSubpartDeclarator):
    """Sentinel for subsystem declaration in a class body.

    See declarative.subsystem for the interface definition.

    """

    @abstractmethod
    def clean_namespace(self, cls_dict: dict):
        """Remove all inner names if the value is the one seen.

        Parameters
        ----------
        cls_dict : dict
            Dictionary from which to remove names belonging only to the
            subpart.

        """
        raise NotImplementedError

    @abstractmethod
    def build_cls(self, parent_name: str, base: type,
                  docs: dict) -> AbstractSubSystem:
        """Build a class based declared base classes and attributes.

        Parameters
        ----------
        parent_name : str
            Name of the parent class system. Used to build the name of the new
            class.

        base : type or None
            Base type for the new class. This class is expected to be a valid
            subclass of for the builder (hence compute_base_classes can be
            skipped). Should  be prepended to any class specified in the
            subpart declaration.

        docs : dict
            Dictionary containing the docstring collected on the parent.

        """
        raise NotImplementedError

    @abstractmethod
    def compute_base_classes(self) -> tuple:
        """Determine the base classes to use when creating a class.

        This should look into the classes stored in the _bases_ attribute and
        return a new tuple of base classes if some necessary classes are not
        present in the specified ones.

        """
        raise NotImplementedError

    @abstractmethod
    def build_descriptor(self, name: str,
                         cls: type) -> AbstractSubSystemDescriptor:
        """Build a descriptor which will be assigned to name.

        """
        pass


class AbstractChannelDeclarator(AbstractSubpartDeclarator):
    """Sentinel for channel declaration in a class body.

    See declarative.channel for the interface definition.

    """

    @abstractmethod
    def build_list_channel_function(self):
        """Build the function responsible for collecting the available channels

        """
        pass


class AbstractSupportMethodCustomization(ABC):
    """Abstract class for objects supporting to have their method customized.

    """

    @abstractmethod
    def modify_behavior(self, method_name: str, func, specifiers: tuple=(),
                        internal: bool=False):
        """Alter the behavior of the Feature using the provided method.

        Those operations are logged into the _customs dictionary in OrderedDict
        for each method so that they can be duplicated by copy_custom_behaviors
        The storing format is as follow : method, name of the operation, args
        of the operation.

        Parameters
        ----------
        method_name : str
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

        modif_id : str
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


class AbstractFeature(property, AbstractSupportMethodCustomization):
    """Abstract class for Features.

    Attributes
    ----------
    name : str
        Name under which this feature is known in the class to which it
        belongs. This is set by the framework.

    creation_kwargs : dict
        Dictionary preserving the arguments with which the feature was
        initialized. This is used when customizing.

    """
    __slots__ = ('creation_kwargs', 'name')

    @abstractmethod
    def make_doc(self, doc: str):
        """Build a comprehensive docstring from the provided user doc and using
        the configuration of the feature.

        """
        pass

    @abstractmethod
    def create_default_settings(self):
        """Create the default settings for a feature.

        """
        pass

    @abstractmethod
    def clone(self):
        """Create a clone of itself.

        """
        pass


class AbstractOptions(AbstractFeature):
    """Abstract class for Options features.

    Options features are used to represent "hardware" options that cannot
    change while the system is connected to the instrument. Options name should
    only be used once inside a driver.

    """
    pass


class AbstractFeatureModifier(ABC):
    """Abstract class for feature modifiers.

    """

    @abstractmethod
    def customize(self, feature: AbstractFeature) -> AbstractFeature:
        """Customize a feature and return a new instance.

        """
        pass


class AbstractAction(AbstractSupportMethodCustomization):
    """Abstract class for actions.

    Attributes
    ----------
    name : str
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

    @abstractmethod
    def create_default_settings(self) -> dict:
        """Create the default settings for an action.

        """
        raise NotImplementedError

    @abstractmethod
    def clone(self):
        """Create a clone of itself.

        """
        pass


class AbstractActionModifier(ABC):
    """Abstract class for action modifiers.

    """

    @abstractmethod
    def customize(self, action) -> AbstractAction:
        """Customize an action and return a new instance.

        """
        pass


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


class AbstractLimitDeclarator(ABC):
    """Abstract class for limits declaration.

    """

    @abstractmethod
    def __call__(self, func):
        """Decorate a function to use to compute limits.

        Should return itself.

        """
        pass


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

        decorate_name : str
            Name uder which the customization function appear in the class
            declaration.

        """
        pass
