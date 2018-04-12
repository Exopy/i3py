# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tools for customization of method using declarative syntax.

"""
from abc import abstractmethod, abstractproperty
from collections import Mapping, OrderedDict
from inspect import Signature, signature
from types import MethodType
from typing import (Any, Callable, ClassVar, Dict, List, Optional, Sequence,
                    Tuple, Type)

from .abstracts import (AbstractMethodCustomizer,
                        AbstractSupportMethodCustomization)


# XXX rework for keyword only args
def normalize_signature(sig: Signature,
                        alias: Optional[str]=None) -> Tuple[str, ...]:
    """Normalize a function signature for quick matching.

    Parameters
    ----------
    sig : Signature
        Function signature

    alias: str, optional
        Alias for self to use in signature.

    Returns
    -------
    normalized : tuple
        Tuple of strings matching the functions arguments, *args and **kwargs
        will have their * preceding.

    """
    def norm_arg(arg, alias):
        if alias and arg.name == 'self':
            return alias
        elif arg.kind == arg.VAR_POSITIONAL:
            return '*' + arg.name
        elif arg.kind == arg.VAR_KEYWORD:
            return '**' + arg.name
        else:
            return arg.name

    return tuple(norm_arg(p, alias) for p in sig.parameters.values())


class MethodComposer(object):
    """Function like object used to compose feature methods calls.

    All methods to call are kept in an ordered fashion ensuring that they will
    be called in the right order while allowing fancy insertion based on method
    id.

    Parameters
    ----------
    obj : SupportMethodCustomization
        Object whose method is customized through the use of a MethodComposer.

    func : callable
        Original function this composer is replacing. This should be a function
        and not a bound method.

    alias : str
        Name to use to replace 'self' in method signature.

    chain_on : str
        Comma separated list of functions arguments that are also values
        returned by the function.

    func_id : str, optional
        Id of the original function to use in the composer.

    Notes
    -----
    Method ids must be unique and duplicate names are removed without warning.

    """
    #: Dict storing custom class for each signature
    signatures: ClassVar[Dict[Tuple[Tuple[Tuple[str, ...], ...], str],
                         Type['MethodComposer']]] = {}

    __slots__ = ('__self__', '__name__', '_alias', '_chain_on', '_names',
                 '_methods', '_signatures')

    #:
    __self__: Any

    _alias: str

    _chain_on: str

    _names: list

    _methods: list

    _signatures: List[Tuple[str, ...]]

    def __new__(cls, obj: AbstractSupportMethodCustomization,
                func: Callable, alias: str, chain_on: str,
                func_id: str='old',
                signatures: Optional[Sequence[Tuple[str, ...]]]=None):
        """Create a custom subclass for each signature function.

        Parameters
        ----------
        obj : SupportMethodCustomization
            Object whose method is customized through the use of a
            MethodComposer.

        func : callable
            Original function this composer is replacing. This should be a
            function and not a bound method.

        alias : str
            Name to use to replace 'self' in method signature.

        chain_on : str
            Comma separated list of functions arguments that are also values
            returned by the function.

        func_id : str, optional
            Id of the original function to use in the composer.

        signatures : list, optional
            List of signatures to accept. If specified the signatures of the
            passed function is ignored and the __call__ method will have the
            signature of the first specified signature.

        """
        if not signatures:
            signatures = [normalize_signature(signature(func), alias)]

        id_ = (tuple(signatures), chain_on)
        if id_ not in MethodComposer.signatures:
            subclass = cls.create_composer(func.__name__, signatures, chain_on)
            MethodComposer.signatures[id_] = subclass

        custom_type = MethodComposer.signatures[id_]
        composer = object.__new__(custom_type)
        composer.__self__ = obj
        composer.__name__ = func.__name__
        composer._alias = alias
        composer._chain_on = chain_on
        composer._methods = [func]
        composer._names = [func_id]
        composer._signatures = signatures
        return composer

    def __call__(self, *args, **kwargs):
        """The signature is customized to match the one of the replaced method.

        """
        pass

    @classmethod
    def create_composer(cls, name: str, sigs: Sequence[Tuple[str, ...]],
                        chain_on: str) -> Type['MethodComposer']:
        """Dynamically create a subclass of base composer for a signature.

        """
        chain = chain_on or ''
        name = '{}Composer'.format(name)
        sig = sigs[0][1:]
        # Should store sig on class attribute
        decl = ('class {name}(cls):\n'
                '    __slots__ = ("sigs",)\n'
                '    def __call__(self{args}):\n'
                '         for m in self._methods:\n'
                '            {ret}m(self.__self__{args})\n'
                '         return {chain}'
                ).format(name=name, args=', ' + ', '.join(sig) if sig else '',
                         chain=chain, ret=chain + ' = ' if chain else '')
        glob = dict(cls=cls)
        exec(decl, glob)
        return glob[name]

    def clone(self,
              new_obj: Optional[AbstractSupportMethodCustomization]=None) -> (
                  'MethodComposer'):
        """Create a full copy of the composer.

        Parameters
        ----------
        new_obj : AbstractSupportMethodCustomization, optional
            New object to which the composer should be bound. If not specified
            The composer is bound to self.__self__.

        """
        new = type(self)(new_obj or self.__self__, self, self._alias,
                         self._chain_on, '', self._signatures)
        new._names = self._names[:]
        new._methods = self._methods[:]
        return new

    def prepend(self, name: str, method: MethodType) -> None:
        """Prepend a method to existing ones.

        Parameters
        ----------
        name : str
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._check_duplicates(name)
        self._names.insert(0, name)
        self._methods.insert(0, method)

    def append(self, name: str, method: MethodType) -> None:
        """Append a method to existing ones.

        Parameters
        ----------
        name : str
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._check_duplicates(name)
        self._names.append(name)
        self._methods.append(method)

    def add_after(self, anchor: str, name: str, method: MethodType) -> None:
        """Add the given method after a given one.

        Parameters
        ----------
        anchor : str
            Id of the method after which to insert the given one.
        name : str
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._check_duplicates(name)
        i = self._names.index(anchor)
        self._names.insert(i+1, name)
        self._methods.insert(i+1, method)

    def add_before(self, anchor: str, name: str, method: MethodType) -> None:
        """Add the given method before the specified one.

        Parameters
        ----------
        anchor : str
            Id of the method before which to insert the given one.
        name : str
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._check_duplicates(name)
        i = self._names.index(anchor)
        self._names.insert(i, name)
        self._methods.insert(i, method)

    def replace(self, name: str, method: MethodType) -> None:
        """Replace an existing method by a new one.

        Only custom methods can be replaced. Methods whose presence is
        linked to the feature kwargs cannot be replaced.

        Parameters
        ----------
        name : str
            Id of the method of the method to replace.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        i = self._names.index(name)
        self._methods[i] = method

    def remove(self, name: str) -> None:
        """Remove a method.

        Parameters
        ----------
        name : str
            Id of the method to remove.

        """
        i = self._names.index(name)
        del self._names[i]
        del self._methods[i]

    def reset(self) -> None:
        """Empty the composer.

        """
        self._names = []
        self._methods = []

    def __getitem__(self, key: str) -> MethodType:
        return self._methods[self._names.index(key)]

    def __contains__(self, item: str) -> bool:
        return item in self._names

    @property
    def __func__(self) -> 'MethodComposer':
        return self

    def _check_duplicates(self, name: str) -> None:
        """Avoid duplicate ids.

        """
        if name in self._names:
            msg = ('Cannot have duplicate ids in MethodComposer. (provided={},'
                   ' existing={})')
            raise ValueError(msg.format(name, self._names))


class customize(AbstractMethodCustomizer):
    """Marks a method to be used for customization of a descriptor method.

    Parameters
    ----------
    desc_name : str
        Name of the object to customize.

    meth_name : str
        Name of the method of the object to customize.

    specifiers : tuple, optional
        Tuple describing the modification. If ommitted the function will simply
        replace the existing behavior otherwise it will be used to update the
        MethodComposer in the adequate fashion.
        The tuple content should be :
        - kind of modification : 'prepend', 'add_before', 'add_after',
          'append', replace', 'remove'
        - argument to the modifier, not necessary for prepend and append.
          It should refer to the id of a previous modification.
        ex : ('add_after', 'old')

    modif_id : str, optional
        Id of the modification used to identify it.

    """
    #: Function to use to modify the behavior of the customized method
    func: Optional[Callable]

    __slots__ = ('desc_name', 'meth_name', 'specifiers', 'modif_id', 'func',
                 '__name__')

    def __init__(self, desc_name: str, meth_name: str,
                 specifiers: Optional[Tuple[str, ...]]=(),
                 modif_id: str='custom') -> None:
        self.desc_name = desc_name
        self.meth_name = meth_name
        self.specifiers = specifiers
        self.modif_id = modif_id
        self.func = None

    def __call__(self, func: Callable) -> 'customize':
        self.func = func
        self.__name__ = func.__name__
        return self

    def customize(self,
                  owner: AbstractSupportMethodCustomization,
                  decorated_name: str):
        """Customize the object owned by owner.

        Parameters
        ----------
        owner : SupportMethodCustomization
            Class owning the descriptor to customize.

        decorated_name : str
            Name under which the customization function appear in the class
            declaration.

        """
        spec = self.specifiers
        if not self.func and (not spec or spec[0] != 'remove'):
            raise RuntimeError('Need to decorate a function before calling '
                               'customize.')
        desc = getattr(owner, self.desc_name)
        assert isinstance(desc, AbstractSupportMethodCustomization),\
            ('Can only customize subclass of '
             'AbstractSupportMethodCustomization.')
        desc.modify_behavior(self.meth_name, self.func, self.specifiers,
                             self.modif_id)


class SupportMethodCustomization:
    """Abstract class for objects supporting to have their method customized.

    """
    #: Name of the object. Used in error reporting.
    name: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = ''
        self._customs: Dict[str, Dict[str, tuple]] = OrderedDict()
        # Ids to use to refer to the old method when replacing it with a
        # composer.
        self._old_ids = {}

    @abstractmethod
    def analyse_function(self, meth_name: str, func: Callable,
                         specifiers: Tuple[str, ...]):
        """Analyse the possibility to use a function for a method.

        Parameters
        ----------
        meth_name : str
            Name of the method that should be customized using the provided
            function.

        func : callable
            Function to use to customize the method.

        specifiers : tuple
            Tuple describing the attempted modification.

        Returns
        -------
        specifiers : tuple
            Tuple describing the attempted modification. It is returned to
            allow altering it. The main use case is turning a complex operation
            in a replace because the base function is a no-op.

        signatures : list
            List of signatures that should be supported by a composer.

        chain_on : str
            Comma separated list of functions arguments that are also values
            returned by the function.

        Raises
        ------
        ValueError :
            Raised if the signature of the provided function does not match the
            one of the customized method.

        """
        pass

    @abstractproperty
    def self_alias(self) -> str:
        """Name used instead of self in function signature.

        """
        pass

    def modify_behavior(self, method_name: str, func: Callable,
                        specifiers: Optional[Tuple[str, ...]]=(),
                        modif_id: str='custom',
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
            ex : ('add_after', 'old')

        modif_id : str, optional
            Id of the modification, used to refer to it in later modification.
            It is this id that can be specified as target for 'add_before',
            'add_after', 'replace', remove'.

        internal : bool, optional
            Private flag used to indicate that this method is used for internal
            purposes and that the modification makes no sense to remember as
            this won't have to be copied by copy_custom_behaviors.

        """
        # Intented full replacement should not have the id custom but 'old' to
        # match a previously present method.
        modif_id = modif_id if specifiers else 'old'

        # In case of non internal modifications (ie unrelated to object
        # initialisation) we keep a description of what has been done to be
        # able to copy those behaviors.
        # This is done before analysing the function to preserve the real
        # intented modification even if the analysis simplify it.
        if not internal:
            original_specifiers = specifiers
            if not specifiers:
                self._customs[method_name] = func
            elif method_name not in self._customs:
                self._customs[method_name] = OrderedDict()
            elif not isinstance(self._customs[method_name], OrderedDict):
                old = self._customs[method_name]
                self._customs[method_name] = OrderedDict(old=(old,
                                                              ('prepend',)))

        # Check the function signature match the targeted method and return
        # the comma separated list of arguments on which the composed called
        # should be chained. Also attempt to simplify the modification if the
        # current function is known to be a no-op.
        if not specifiers or specifiers[0] != 'remove':
            specifiers, sigs, chain_on = self.analyse_function(method_name,
                                                               func,
                                                               specifiers)
        else:
            sigs, chain_on = None, None

        # In the absence of specifiers or for get and set we simply replace the
        # method.
        if not specifiers:
            # Preserve the id in case of future mofication
            self._old_ids[method_name] = modif_id
            setattr(self, method_name, MethodType(func, self))
            # For an intended full replacement we already logged the operation
            if not internal and not original_specifiers:
                return

        else:
            # Otherwise we make sure we have a MethodsComposer.
            composer = getattr(self, method_name)
            if not isinstance(composer, MethodComposer):
                # Try to get a smart id from the object in case it was set by a
                # a previous modification.
                composer = MethodComposer(self, composer.__func__,
                                          self.self_alias, chain_on,
                                          self._old_ids.get(method_name,
                                                            'old'),
                                          signatures=sigs)

            # We now update the composer.
            composer_method_name = specifiers[0]
            composer_method = getattr(composer, composer_method_name)
            if composer_method_name in ('add_before', 'add_after'):
                composer_method(specifiers[1], modif_id, func)
            elif composer_method_name == 'replace':
                composer_method(specifiers[1], func)
            elif composer_method_name == 'remove':
                composer_method(specifiers[1])
            else:
                composer_method(modif_id, func)

            # Finally we reassign the composer.
            setattr(self, method_name, composer)

        # Finally we update the _customs dict
        if not internal:
            customs = self._customs[method_name]
            if original_specifiers[0] == 'remove':
                del customs[modif_id]
            elif original_specifiers[0] == 'replace':
                replaced = specifiers[1]
                if replaced in customs:
                    old = list(customs[replaced])
                    old[0] = func
                    customs[replaced] = tuple(old)
                else:
                    ind = composer._names.index(replaced)
                    if ind == 0:
                        customs[replaced] = (func, ('prepend',))
                    else:
                        n = composer._names[ind-1]
                        customs[replaced] = (func, ('add_after', n))
            else:
                op = (func, original_specifiers)
                customs[modif_id] = op

    def copy_custom_behaviors(self, obj: AbstractSupportMethodCustomization):
        """Copy the custom behaviors existing on an object to this one.

        This is used to preserve the custom behaviors after recreating an
        object with different kwargs or cloning it. If an add_before or
        add_after clause cannot be satisfied because the anchor disappeared
        this method tries to insert the custom method in the most likely
        position.

        CAUTION : This method strives to build something that makes sense but
        it will most likely fail in some weird corner cases so avoid as mush as
        possible to use set_feat on feature modified using specially named
        method on the driver.

        """
        # Loop on methods which are affected by mofifiers.
        for meth_name, modifiers in obj._customs.items():
            if not isinstance(modifiers, Mapping):
                # In this case modifiers is a function describing a replacement
                self.modify_behavior(meth_name, modifiers)
                continue

            # Loop through all the modifications.
            for custom, modifier in modifiers.items():

                func, specifiers = modifier
                method = getattr(self, meth_name)
                # In the absence of anchor we simply attempt the operation.
                if specifiers[0] not in ('add_after', 'add_before'):
                    self.modify_behavior(meth_name, func, specifiers, custom)

                # If the method is not a method composer there is no point in
                # attempting an operation involving an anchor.
                elif not isinstance(method, MethodComposer):
                    aux = {'add_after': ('append',),
                           'add_before': ('prepend',)}
                    self.modify_behavior(meth_name, func, aux[specifiers[0]],
                                         custom)

                # Otherwise we check whether or not the anchor exists and if
                # not try to find the most meaningfull one.
                else:
                    our_names = method._names
                    if specifiers[1] in our_names:
                        self.modify_behavior(meth_name, func, specifiers,
                                             custom)
                    else:
                        names = getattr(obj, meth_name)._names
                        # For add after we try to find an entry existing in
                        # both feature going backward (we will prepend at the
                        # worst), for add before we go forward (we will append
                        # in the absence of match).
                        shift = -1 if specifiers[0] == 'add_after' else -1
                        index = names.index(custom)
                        while index > 0 and index < len(names)-1:
                            index += shift
                            name = names[index]
                            if name in our_names:
                                self.modify_behavior(meth_name, func,
                                                     (specifiers[0], name),
                                                     custom)
                                shift = 0
                                break

                        if shift != 0:
                            op = ('prepend' if shift == -1 else 'append',)
                            self.modify_behavior(meth_name, func, op, custom)


AbstractSupportMethodCustomization.register(SupportMethodCustomization)
