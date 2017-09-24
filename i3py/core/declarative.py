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
from abc import abstractmethod
from inspect import currentframe

from .abstracts import ABC, AbstractSubSystem, AbstractChannel

# Sentinel returned when decorating a method with a subpart.
SUBPART_FUNC = object()


class SubpartDecl(ABC):
    """Sentinel used to collect declarations or modifications for a subpart.

    Parameters
    ----------
    bases : class or tuple of classes, optional
        Class or classes to use as base class when no matching subpart exists
        on the driver.

    """
    def __init__(self, bases=(), attributes=None):
        self._name_ = ''
        if not isinstance(bases, tuple):
            bases = (bases,)
        self._bases_ = bases
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
            Dummy letting the metaclass to remove this from the class
            definition.

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

    def clean_namespace(self, cls_dict):
        """Remove all inner names if the value is the one seen.

        Parameters
        ----------
        cls_dict : dict
            Dictionary from which to remove names belonging only to the
            subpart.

        """
        for k, v in self._inners_.items():
            if k in cls_dict and cls_dict[k] is v:
                del cls_dict[k]

    def build_cls(self, parent_name, base, docs):
        """Build a class based declared base classes and attributes.

        Parameters
        ----------
        parent_name : unicode
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
        # Python 2 fix : class name can't be unicode
        name = str(parent_name + self._name_.capitalize())
        dct = dict(self.__dict__)
        del dct['_name_']
        del dct['_parent_']
        del dct['_bases_']
        del dct['_aliases_']
        del dct['_enter_locals_']
        del dct['_inners_']
        dct['_docs_'] = docs
        new_class = meta(name, bases, dct)
        new_class.__doc__ = part_doc
        return new_class

    @abstractmethod
    def compute_base_classes(self):
        """Determine the base classes to use when creating a class.

        This should look into the classes stored in the _bases_ attribute and
        return a new tuple of base classes if some necessary classes are not
        present in the specified ones.

        """
        pass


class subsystem(SubpartDecl):
    """Sentinel used to collect declarations or modifications for a subsystem.

    Parameters
    ----------
    bases : class or tuple of classes, optional
        Class or classes to use as base class when no matching subpart exists
        on the driver.

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


class channel(SubpartDecl):
    """Sentinel used to collect declarations or modifications for a channel.


    Parameters
    ----------
    available : unicode, tuple or list, optional
        Name of the parent method to call to know which channels exist or list
        of channel ids. If absent the channel declaration on the base class is
        used instead.

    bases : class or tuple of classes, optional
        Class or classes to use as base class when no matching subpart exists
        on the driver.

    aliases : dict, optional
        Dictionary providing aliases for channels ids. Aliases can be simple
        values, list or tuple.

    container_type : type, optional
        Container type to use to store channels.

    """
    def __init__(self, available=None, bases=(), aliases=None,
                 container_type=None):
        super(channel, self).__init__(bases)
        self._available_ = available
        self._ch_aliases_ = aliases if aliases else {}
        self._container_type_ = container_type
        if container_type is None:
            from .base_channel import ChannelContainer
            self._container_type_ = ChannelContainer

    def build_cls(self, parent_name, base, docs):
        """Reimplemented to set the _container_type_ attribute.

        """
        cls = super(channel, self).build_cls(parent_name, base, docs)
        cls._container_type_ = self._container_type_
        cls._part_ = self
        return cls

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


class set_feat(ABC):
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


class set_action(ABC):
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


class limit(ABC):
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
