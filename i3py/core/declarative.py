# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Helpers used to write driver classes in a declarative way.

"""
from inspect import currentframe

from .abstracts import (AbstractSubpartDeclarator,
                        AbstractSubSystem, AbstractSubSystemDeclarator,
                        AbstractChannel, AbstractChannelDeclarator,
                        AbstractFeatureModifier, AbstractActionModifier,
                        AbstractLimitDeclarator)
from .utils import build_checker

# Sentinel returned when decorating a method with a subpart.
SUBPART_FUNC = object()


class SubpartDecl(object):
    """Sentinel used to collect declarations or modifications for a subpart.

    Parameters
    ----------
    bases : class or tuple of classes, optional
        Class or classes to use as base class when no matching subpart exists
        on the driver.

    checks : str, optional
        Booelan tests to execute before anything else when attempting use a
        Feature or an Action of the subpart. Multiple assertion can be
        separated with ';'. The subpart can be accessed through the name
        driver just like in features.

    options : str, optional
        Assertions in the form option_name['option_field'] == possible_values
        or any other valid boolean test. Multiple assertions can be separated
        by ;

    descriptor_type : type
        Class to use as descriptor for this subpart.

    """
    __slots__ = ('_name_', '_bases_', '_checks_', '_options_',
                 '_descriptor_type_', '_parent_', '_aliases_', '_inners_',
                 '_enter_locals_')

    def __init__(self, bases=(), checks='', options=None,
                 descriptor_type=None):
        self._name_ = ''
        if not isinstance(bases, tuple):
            bases = (bases,)
        self._bases_ = bases
        self._checks_ = checks
        self._options_ = options
        self._descriptor_type_ = descriptor_type
        self._parent_ = None
        self._aliases_ = []
        self._inners_ = {}
        self._enter_locals_ = None

    def __setattr__(self, name, value):
        if isinstance(value, SubpartDecl):
            object.__setattr__(value, '_parent_', self)
        object.__setattr__(self, name, value)

    def __call__(self, func):
        """Decorator maker to register functions in the subpart.

        The function is stored in the object under its own name.

        Returns
        -------
        ret : SUBPART_FUNC
            Dummy left for the metaclass to remove from the class definition.

        """
        object.__setattr__(self, func.__name__, func)
        return SUBPART_FUNC

    def __enter__(self):
        """Using this a context manager helps readability and can allow to
        use shorter names in declarations.

        """
        self._enter_locals_ = currentframe().f_back.f_locals.copy()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """"Using this a context manager helps readability and can allow to
        use shorter names in declarations.

        When exiting we identify seen names that will be removed later by the
        enclosing class to avoid leaking subpart only declarations into the
        main class. We also discover the aliases used for this subpart which
        are later used to collect the docstrings of the features.

        """
        frame = currentframe().f_back
        frame_locals = frame.f_locals
        diff = set(frame_locals) - set(self._enter_locals_)
        aliases = {k: v for k, v in frame_locals.items()
                   if k in diff and v is self}
        self._aliases_.extend(aliases)
        self._enter_locals_ = None
        self._inners_ = {k: v for k, v in frame_locals.items() if k in diff}

    def clean_namespace(self, cls):
        """Remove all inner names if the value is the one seen.

        Parameters
        ----------
        cls : type
            Class from which to remove names belonging only to the
            subpart.

        """
        for k, v in self._inners_.items():
            if k in cls.__dict__ and getattr(cls, k) is v:
                delattr(cls, k)

    def build_cls(self, parent_cls, base, docs):
        """Build a class based declared base classes and attributes.

        Parameters
        ----------
        parent_cls : Type
            Parent class system. Used to build the name of the new class and
            identify if the parent class can be disabled at runtime.

        base : type or None
            Base type for the new class. This class is expected to be a valid
            subclass of for the builder (hence compute_base_classes can be
            skipped). Should  be prepended to any class specified in the
            subpart declaration.

        docs : dict
            Dictionary containing the docstring collected on the parent.

        """
        # If provided prepend base to declared base classes.
        if base:
            bases = tuple([base] + list(self._bases_))

        # Otherwise check that we have a SubSystem or Channel subclass in the
        # mro and if not prepend it.
        else:
            bases = self.compute_base_classes()

        # Extract the docstring specific to this subpart.
        part_doc = docs.get(self._name_, '')
        s_docs = {tuple(k.split('.', 1)): v for k, v in docs.items()}
        docs = {k[-1]: v for k, v in s_docs.items()
                if k[0] in self._aliases_ and len(k) == 2}
        meta = type(bases[0])
        name = parent_cls.__name__ + self._name_.capitalize()

        # Add docs to the class dictionary before creation (the slots are not
        # listed in __dict__)
        dct = dict(self.__dict__)
        dct['_docs_'] = docs

        # Add a custom descriptor for enabling if the subsystem declares checks
        if self._checks_:
            func = build_checker(self._checks_, '(driver)', 'True')

            def enabled_getter(driver):
                """Check this subpart and all its parents are enabled.

                """
                if not driver.parent._enabled_:
                    driver._enabled_error_ = driver.parent._enabled_error_
                    return False
                try:
                    return func(driver), ''
                except AssertionError as e:
                    driver._enabled_error_ = e
                    return False

            dct['_enabled_'] = property(enabled_getter)

        # Add a custom descriptor for enabling if the subpart parent has one
        elif hasattr(parent_cls, '_enabled_'):

            def enabled_getter(driver):
                """Check all of this subpart parents are enabled.

                """
                if not driver.parent._enabled_:
                    driver._enabled_error_ = driver.parent._enabled_error_
                    return False
                return True

            dct['_enabled_'] = property(enabled_getter)

        new_class = meta(name, bases, dct)
        new_class.__doc__ = part_doc
        new_class._declaration_ = self

        return new_class

    def update_from_ancestor(self, ancestor_decl):
        """Update the declaration with parameters from inherited subpart.

        """
        self._descriptor_type_ = (self._descriptor_type_ or
                                  ancestor_decl._descriptor_type_)
        if ancestor_decl._checks_:
            self._checks_ = (';'.join(self._checks_, ancestor_decl._checks_)
                             if self._checks_ else ancestor_decl._checks_)
        if ancestor_decl._options_:
            self._options_ = (';'.join(self._options_, ancestor_decl._options_)
                              if self._options_ else ancestor_decl._options_)

    def compute_base_classes(self):
        """Determine the base classes to use when creating a class.

        This should look into the classes stored in the _bases_ attribute and
        return a new tuple of base classes if some necessary classes are not
        present in the specified ones.

        """
        raise NotImplementedError

    def build_descriptor(self):
        """Build the descriptor used access the subpart from the driver.

        """
        raise NotImplementedError


AbstractSubpartDeclarator.register(SubpartDecl)


class subsystem(SubpartDecl):
    """Sentinel used to collect declarations or modifications for a subsystem.

    Parameters
    ----------
    bases : class or tuple of classes, optional
        Class or classes to use as base class when no matching subpart exists
        on the driver.

    checks : str, optional
        Booelan tests to execute before anything else when attempting use a
        Feature or an Action of the subsytem. Multiple assertion can be
        separated with ';'. The subsystem can be accessed through the name
        driver just like in features.

    options : str, optional
        Assertions in the form option_name['option_field'] == possible_values
        or any other valid boolean test. Multiple assertions can be separated
        by ;

    descriptor_type : type
        Class to use as descriptor for this subsystem. Should be a sunclass of
        AbstractSubSystemDescriptor.

    """
    def compute_base_classes(self):
        """Add SubSystem in the base classes if necessary.

        The first class should always be a SubSystem subclass so prepend if it
        is not so.

        """
        bases = self._bases_
        if not bases or not issubclass(bases[0], AbstractSubSystem):
            from .base_subsystem import SubSystem
            bases = (SubSystem,) + bases

        return bases

    def build_descriptor(self, name, cls):
        """Build the descriptor that will be used to access the subsystem.

        Parameters
        ----------
        name : str
            Name under which the descriptor will be stored on the instance.

        cls : type
            Class built by a previous call to build_cls.

        """
        if self._descriptor_type_ is None:
            from .base_subsystem import SubSystemDescriptor
            dsc_type = SubSystemDescriptor
        else:
            dsc_type = self._descriptor_type_

        return dsc_type(cls, name, self._options_)


AbstractSubSystemDeclarator.register(subsystem)


class channel(SubpartDecl):
    """Sentinel used to collect declarations or modifications for a channel.


    Parameters
    ----------
    available : str, tuple or list, optional
        Name of the parent method to call to know which channels exist or list
        of channel ids. If absent the channel declaration on the base class is
        used instead.

    bases : class or tuple of classes, optional
        Class or classes to use as base class when no matching subpart exists
        on the driver.

    aliases : dict, optional
        Dictionary mapping channel ids to their allowed aliases. Aliases can be
        simple values, list or tuple.

    container_type : type, optional
        Container type to use to store channels.

    checks : str, optional
        Booelan tests to execute before anything else when attempting use a
        Feature or an Action of the chnnel. Multiple assertion can be separated
        with ';'. The channel can be accessed through the name driver just like
        in features.

    options : str, optional
        Booelan tests on options to execute before creating the subpart.
        Multiple assertion can be separated with ';'. The options can be
        accessed under their name directly:

    descriptor_type : type
        Class to use as descriptor for this subpart. Should be a sunclass of
        AbstractSubSystemDescriptor.

    """
    def __init__(self, available=None, bases=(), aliases=None,
                 container_type=None, options=None, checks=None,
                 descriptor_type=None):
        super().__init__(bases, checks, options, descriptor_type)
        self._available_ = available
        self._ch_aliases_ = aliases if aliases else {}
        self._container_type_ = container_type

    def update_from_ancestor(self, ancestor_decl):
        """Update the declaration with parameters from inherited subpart.

        """
        super().update_from_ancestor(ancestor_decl)
        self._available_ = self._available_ or ancestor_decl._available_
        self._ch_aliases_.update(ancestor_decl._ch_aliases_)
        self._container_type_ = (self._container_type_ or
                                 ancestor_decl._container_type_)

    def compute_base_classes(self):
        """Add Channel in the base classes if necessary.

        The first class should always be a Channel subclass so prepend if it
        is not so.

        """
        bases = self._bases_
        if not bases or not issubclass(bases[0], AbstractChannel):
            from .base_channel import Channel
            bases = (Channel,) + (bases)
        return bases

    def build_list_channel_function(self):
        """Build the function used to list the available channels.

        """
        if isinstance(self._available_, (tuple, list)):
            return lambda driver: self._available_

        else:
            return lambda driver: getattr(driver, self._available_)()

    def build_descriptor(self, name, cls):
        """Build the descriptor that will be used to access the channel.

        Parameters
        ----------
        name : str
            Name under which the descriptor will be stored on the instance.

        cls : type
            Class built by a previous call to build_cls.

        """
        if self._descriptor_type_ is None:
            from .base_channel import ChannelDescriptor
            dsc_type = ChannelDescriptor
        else:
            dsc_type = self._descriptor_type_

        if self._container_type_ is None:
            from .base_channel import ChannelContainer
            ctn_type = ChannelContainer
        else:
            ctn_type = self._container_type_

        list_func = self.build_list_channel_function()
        return dsc_type(cls, name, self._options_, ctn_type, list_func,
                        self._ch_aliases_)


AbstractChannelDeclarator.register(channel)


class set_feat(object):
    """Placeholder used to alter a feature in a subclass.

    This can be used to lightly alter a Feature defined on a parent class
    by for example changing the retries or the getter but without
    rewriting everything.

    Parameters
    ----------
    **kwargs
        New keyword arguments to pass to the constructor to alter the Feature.

    """
    def __init__(self, **kwargs):
        self.custom_attrs = kwargs

    def customize(self, feat):
        """Customize a feature using the given kwargs.

        """
        cls = type(feat)
        kwargs = feat.creation_kwargs.copy()
        kwargs.update(self.custom_attrs)
        new = cls(**kwargs)
        new.copy_custom_behaviors(feat)

        return new

AbstractFeatureModifier.register(set_feat)


class set_action(object):
    """Placeholder used to alter an action in a subclass.

    This can be used to lightly alter an Action defined on a parent class.

    Parameters
    ----------
    **kwargs
        New keyword arguments to pass to the constructor to alter the Action.

    """
    def __init__(self, **kwargs):
        self.custom_attrs = kwargs

    def customize(self, action):
        """Customize an action using the given kwargs.

        """
        cls = type(action)
        kwargs = action.creation_kwargs.copy()
        kwargs.update(self.custom_attrs)
        new = cls(**kwargs)

        new(action.func)
        new.copy_custom_behaviors(action)

        return new


AbstractActionModifier.register(set_action)


class limit(object):
    """Class to use as a decorator to mark a function as defining a limit.

    The decorated function should take as argument the driver part matching
    the level at which it is defined, (ie self) and return an
    `AbstractLimitsValidator`.

    """
    __slots__ = ('name', 'func')

    def __init__(self, limit_name=None):
        self.name = limit_name

    def __call__(self, func):
        self.func = func
        return self


AbstractLimitDeclarator.register(limit)
