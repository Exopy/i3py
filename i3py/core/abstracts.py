# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Abstract classes used in I3py.

"""
from abc import ABC, abstractclassmethod, abstractmethod, abstractproperty
from inspect import Signature
from types import MethodType
from typing import (Any, Callable, ClassVar, Dict, Hashable, Iterable, Mapping,
                    Optional, Tuple, Type, Union)


class AbstractHasFeatures(ABC):
    """Sentinel class for the collections of Features.

    """
    #: Dictionary containing all the features of the class by name. The values
    #: are instances of AbstractFeature.
    __feats__: ClassVar[Dict[str, 'AbstractFeature']] = {}

    #: Dictionary containing all the actions of the class by name. The values
    #: are instances of AbstractAction.
    __actions__: ClassVar[Dict[str, 'AbstractAction']] = {}

    #: Dictionary containing all the subsystems of the class by name. The
    #: values are subclasses of AbstractSubSystem.
    __subsystems__: ClassVar[Dict[str, 'AbstractSubSystem']] = {}

    #: Dictionary containing all the channels of the class by name. The
    #: values are subclasses of AbstractChannel.
    __channels__: ClassVar[Dict[str, 'AbstractChannel']] = {}

    #: Dictionary containing all the limits of the class by name. The
    #: values are the methods, decorated by limit, and in charge of creating
    #: the limit object.
    __limits__: ClassVar[Dict[str, 'AbstractLimitsValidator']] = {}

    #: Tuple of exception to consider when securing a communication (either via
    #: secure_communication decorator or for features with a non zero
    #: retries value)
    retries_exceptions: ClassVar[Tuple[Type[Exception], ...]] = ()

    #: Private member in which instance specific settings for features and
    #: actions can be stored.
    _settings: Dict[str, Dict[str, Any]]

    #: _Private member in which features expect to be able to store values
    #: under their name.
    _cache: Dict[str, Any]

    #: private member in which the exception justifying the component being
    #: disabled can be found.
    _enabled_error_: Exception

    #: Private member used to store the instances of subsystems declared on the
    #: class. This member can be used by AbstractSubsystemDescriptor subclasses
    _subsystem_instances: Optional[Dict[str, 'AbstractSubSystem']]

    #: Private member used to store the instances of channel containers
    #: matching the channels  declared on the  class. This member can be used
    #: by AbstractChannelDescriptor subclasses.
    _channel_container_instances: Optional[Dict[str,
                                                'AbstractChannelContainer']]

    #: Should this particular instance use caching
    _use_cache: bool = True

    @abstractmethod
    def __init__(self, caching_allowed: bool=True) -> None:
        pass

    @abstractproperty
    def lock(self) -> Any:
        pass

    @abstractproperty
    def _enabled_(self) -> bool:
        """Is this component is enabled/accessible at runtime.

        This may not be so if a runtime setting of the instrument changed.

        """
        pass

    @abstractmethod
    def default_get_feature(self, feat: 'AbstractFeature', cmd: Any,
                            *args, **kwargs) -> Any:
        """Method used by default by the Feature to retrieve a value from an
        instrument.

        Parameters
        ----------
        feat : Feature
            Reference to the property issuing this call.
        cmd :
            Command used by the implementation to determine what should be done
            to get the answer from the instrument.
        *args :
            Additional arguments necessary to retrieve the instrument state.
        **kwargs :
            Additional keywords arguments necessary to retrieve the instrument
            state.

        """
        pass

    @abstractmethod
    def default_set_feature(self, feat: 'AbstractFeature', cmd: Any,
                            *args, **kwargs) -> Any:
        """Method used by default by the Feature to set an instrument value.

        Parameters
        ----------
        feat : Feature
            Reference to the property issuing this call.
        cmd :
            Command used by the implementation to determine what should be done
            to set the instrument state.
        *args :
            Additional arguments necessary to set the instrument state.
        **kwargs :
            Additional keywords arguments necessary to set the instrument
            state.

        """
        pass

    @abstractmethod
    def default_check_operation(self,
                                feat: 'AbstractFeature',
                                value: Any,
                                i_value: Any,
                                state: Any=None) -> Tuple[bool, Any]:
        """Method used by default by the Feature to check the instrument
        operation.

        Parameters
        ----------
        feat : Feature
            Reference to the Feature issuing this call.
        value :
            Value assigned by the user.
        i_value :
            Value computed by the pre_set method of the Feature.
        state : optional
            State of the instrument if already known.

        Returns
        -------
        result : bool
            Is everything ok ? Can we assume that the last operation succeeded.
        precision :
            Any precision about the situation, this can be any object but
            something should always be returned.

        """
        pass

    @abstractmethod
    def reopen_connection(self):
        """Handle the need to close and re-open a potential bad connection.

        """
        pass

    @abstractmethod
    def clear_cache(self, subsystems: bool=True, channels: bool=True,
                    features: Optional[Iterable[str]]=None):
        """ Clear the cache of all the features or only of the specified
        ones.

        Parameters
        ----------
        subsystems : bool, optional
            Whether or not to clear the subsystems. This argument is used only
            if features is None.
        channels : bool, optional
            Whether or not to clear the channels. This argument is used only
            if features is None.
        features : iterable of str, optional
            Name of the features whose cache should be cleared. Dotted names
            can be used to access subsystems and channels. When accessing
            channels the cache of all instances is cleared. All caches
            will be cleared if not specified.

        """
        pass

    @abstractmethod
    def get_limits(self, limits: str) -> 'AbstractLimitsValidator':
        """Return the limits validator matching the passed name.

        """
        pass

    @abstractmethod
    def discard_limits(self, limits: Iterable[str]) -> None:
        """Discard specified cached limits validators.

        """
        pass


class AbstractBaseDriver(AbstractHasFeatures):
    """Sentinel class for the identification of a driver.

    """
    #: Id of the last 'user' of the driver can be used by framework to keep
    #: track 'who' last interacted with the instrument.
    owner: str

    #: Boolean indicating if the driver that has just been returned is a new
    #: instance or not, because an instance connected to the same instrument
    #: already existed.
    newly_created: bool

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractclassmethod
    def compute_id(cls, args: tuple, kwargs: dict) -> Hashable:
        """Use the arguments to compute a unique id for the instrument.

        This can also be used to alter the content of the kwargs dictionary.
        This is why we do not unpack it.

        Parameters
        ----------
        args :
            Positional arguments passed to the constructor

        kwargs :
            Keyword arguments passed to the constructor.

        Returns
        -------
        id : hashable
            Unique id identifying the instrument this driver is connected to.

        """
        pass

    @abstractmethod
    def initialize(self):
        """Open a connection to an instrument.

        """
        pass

    @abstractmethod
    def finalize(self):
        """Close the connection to the instrument.

        """
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        """Check whether or not the cache is likely to have been corrupted.

        Returns
        -------
        status : bool
            True is the connection can be trusted, False otherwise.

        """
        pass

    @abstractproperty
    def connected(self) -> bool:
        """Return whether or not commands can be sent to the instrument.

        """
        pass

    @abstractmethod
    def __enter__(self) -> 'AbstractBaseDriver':
        """Context manager handling the connection to the instrument.

        """
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager handling the connection to the instrument.

        """
        pass


class AbstractSubSystem(AbstractHasFeatures):
    """Sentinel for subsystem identification.

    """
    #: Parent component (AbstractHasFeature) to which this subsystem is linked.
    parent: AbstractHasFeatures


class AbstractSubSystemDescriptor(property, ABC):
    """Abstract subsystem descriptor.

    """
    pass


class AbstractChannel(AbstractSubSystem):
    """Sentinel class for channel identification.

    """
    #: Parent component (AbstractHasFeature) to which this channel is linked.
    parent: AbstractHasFeatures

    @abstractmethod
    def __init__(self, ch_id: Any, caching_allowed: bool=True) -> None:
        pass


class AbstractChannelContainer(ABC):
    """Abstract container class for instrument channels.

    The interface is defined in the ChannelContainer subclass.

    """
    @abstractmethod
    def __init__(self, cls: Type[AbstractChannel], parent: AbstractHasFeatures,
                 name: str, list_available: Callable, aliases: dict) -> None:
        pass

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

    @abstractmethod
    def __getitem__(self, ch_id: Any):
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
    _customs: Dict[str, Union[Callable, Mapping]]

    @abstractmethod
    def modify_behavior(self, method_name: str, func: Callable,
                        specifiers: tuple=(), modif_id: str='custom',
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
    def copy_custom_behaviors(self, obj: 'AbstractSupportMethodCustomization'):
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

    """
    #: Name under which this feature is known in the class to which it
    #: belongs. This is set by the framework.
    name: str

    #: Dictionary preserving the arguments with which the feature was
    #: initialized. This is used when customizing.
    creation_kwargs: Dict[str, Any]

    __slots__ = ('creation_kwargs', 'name')

    @abstractmethod
    def make_doc(self, doc: str) -> str:
        """Build a comprehensive docstring from the provided user doc and using
        the configuration of the feature.

        """
        pass

    @abstractmethod
    def create_default_settings(self) -> dict:
        """Create the default settings for a feature.

        """
        pass

    @abstractmethod
    def clone(self) -> 'AbstractFeature':
        """Create a clone of itself.

        """
        pass


class AbstractOptions(AbstractFeature):
    """Abstract class for Options features.

    Options features are used to represent "hardware" options that cannot
    change while the system is connected to the instrument. Options name should
    only be used once inside a driver.

    The options are expected to be returned as a dictionary with str keys.

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

    """
    #: Name under which this action is known in the class to which it
    #: belongs. This is set by the framework.
    name: str

    #: Dictionary preserving the arguments with which the action was
    #: initialized. This is used when customizing.
    creation_kwargs: Dict[str, Any]

    #: Function on which the Action has been used as a decorator.
    func: Callable

    #: Signature of the function this action wraps
    sig: Optional[Signature]

    __slots__ = ('creation_kwargs', 'name', 'func')

    @abstractmethod
    def __call__(self, func: Callable) -> Any:
        """Invoked when the class is used as a decorator.

        """
        pass

    @abstractmethod
    def __get__(self,
                obj: AbstractHasFeatures,
                objtype: Optional[Type[AbstractHasFeatures]]=None
                ) -> Union[Callable, Type['AbstractAction']]:
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
    def clone(self) -> 'AbstractAction':
        """Create a clone of itself.

        """
        pass


class AbstractActionModifier(ABC):
    """Abstract class for action modifiers.

    """

    @abstractmethod
    def customize(self, action: AbstractAction) -> AbstractAction:
        """Customize an action and return a new instance.

        """
        pass


class AbstractLimitsValidator(ABC):
    """ Base class for all limits validators.

    """
    #: Minimal allowed value or None.
    minimum: Any

    #: Maximal allowed value or None.
    maximum: Any

    #: Allowed step between values or None.
    step: Any

    #: Validate a given value against the range.
    validate: MethodType

    __slots__ = ('minimum', 'maximum', 'step', 'validate')


class AbstractLimitDeclarator(ABC):
    """Abstract class for limits declaration.

    """

    @abstractmethod
    def __call__(self, func: Callable) -> 'AbstractLimitDeclarator':
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
    def build_getter(self) -> Callable:
        """Build the function for getting the Feature value.

        This method is called when a get/set factory is passed as the getter
        argument to a Feature.

        """
        raise NotImplementedError()

    @abstractmethod
    def build_setter(self) -> Callable:
        """Build the function for setting the Feature value.

        This method is called when a get/set factory is passed as the setter
        argument to a Feature.

        """
        raise NotImplementedError()


class AbstractMethodCustomizer(ABC):
    """Abstract class for object used to specify a modification of a method.

    """
    @abstractmethod
    def __call__(self, func: Callable):
        """Use the method customizer as a decorator.

        """
        pass

    @abstractmethod
    def customize(self, owner: AbstractSupportMethodCustomization,
                  decorated_name: str):
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
