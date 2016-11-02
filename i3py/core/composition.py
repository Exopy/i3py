# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tools for customization of method using declarative syntax.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from types import MethodType
from collections import OrderedDict

from future.utils import with_metaclass

from .abstracts import (AbstractMethodCustomizer,
                        AbstractSupportMethodCustomization)


class MetaMethodComposer(type):
    """
    """

    def __call__(cls, func):
        """
        """
        pass


class MethodComposer(with_metaclass(MetaMethodComposer, object)):
    """Function like object used to compose feature methods calls.

    All methods to call are kept in an ordered dict ensuring that they will
    be called in the right order while allowing fancy insertion based on method
    id.

    Notes
    -----
    Method ids must be unique and duplicate names are removed without warning.

    """
    __slots__ = ('_names', '_methods')

    def __init__(self):
        self._methods = []
        self._names = []

    def clone(self):
        """Create a full copy of the composer.

        """
        new = type(self)()
        new._names = self._names[:]
        new._methods = self._methods[:]
        return new

    def prepend(self, name, method):
        """Prepend a method to existing ones.

        Parameters
        ----------
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._remove_duplicate(name)
        self._names.insert(0, name)
        self._methods.insert(0, method)

    def append(self, name, method):
        """Append a method to existing ones.

        Parameters
        ----------
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._remove_duplicate(name)
        self._names.append(name)
        self._methods.append(method)

    def add_after(self, anchor, name, method):
        """Add the given method after a given one.

        Parameters
        ----------
        anchor : unicode
            Id of the method after which to insert the given one.
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._remove_duplicate(name)
        i = self._names.index(anchor)
        self._names.insert(i+1, name)
        self._methods.insert(i+1, method)

    def add_before(self, anchor, name, method):
        """Add the given method before the specified one.

        Parameters
        ----------
        anchor : unicode
            Id of the method before which to insert the given one.
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._remove_duplicate(name)
        i = self._names.index(anchor)
        self._names.insert(i, name)
        self._methods.insert(i, method)

    def replace(self, name, method):
        """Replace an existing method by a new one.

        Only custom methods can be replaced. Methods whose presence is
        linked to the feature kwargs cannot be replaced.

        Parameters
        ----------
        name : unicode
            Id of the method of the method to replace.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        i = self._names.index(name)
        self._methods[i] = method

    def remove(self, name):
        """Remove a method.

        Parameters
        ----------
        name : unicode
            Id of the method to remove.

        """
        i = self._names.index(name)
        del self._names[i]
        del self._methods[i]

    def reset(self):
        """Empty the composer.

        """
        self._names = []
        self._methods = []

    def __getitem__(self, key):
        return self._methods[self._names.index(key)]

    def __contains__(self, item):
        return item in self._names

    def _remove_duplicate(self, name):
        """Remove the name from the list to avoid having duplicate ids.

        """
        if name in self._names:
            i = self._names.index(name)
            del self._names[i]
            del self._methods[i]


class MethodCustomizer(AbstractMethodCustomizer):
    """
    """
    __slots__ = ('obj_name', 'meth_name', 'modifiers')

    def __init__(self, obj_name, meth_name, modifiers, modif_id):
        pass

    def customize(self, owner, decorated_name):
        """
        """
        pass


class SupportMethodCustomization(AbstractSupportMethodCustomization):
    """Abstract class for objects supporting to have their method customized.

    """

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
            - id of the modification, used to refer to it in later modification
            - kind of modification : 'prepend', 'add_before', 'add_after',
              'append', replace', 'remove'
            - argument to the modifier, necessary only for 'add_after',
              'add_before' and should refer to the id of a previous
              modification.
            ex : ('custom', 'add_after', 'old')

        internal : bool, optional
            Private flag used to indicate that this method is used for internal
            purposes and that the modification makes no sense to remember as
            this won't have to be copied by copy_custom_behaviors.

        """
        # In the absence of specifiers or for get and set we simply replace the
        # method.
        if not specifiers:
            setattr(self, method_name, func)
            if not internal:
                self._customs[method_name] = func
            return

        # Otherwise we make sure we have a MethodsComposer.
        composer = getattr(self, method_name)
        if not isinstance(composer, MethodComposer):
            composer = MethodComposer(composer)

        # In case of non internal modifications (ie unrelated to object
        # initialisation) we keep a description of what has been done to be
        # able to copy those behaviors. If a method already existed we assume
        # it was meaningful and add it in the composer under the id 'old'.
        if not internal:
            if method_name not in self._customs:
                self._customs[method_name] = OrderedDict()
            elif not isinstance(self._customs[method_name], OrderedDict):
                old = self._customs[method_name]
                composer.prepend('old', old)
                self._customs[method_name] = OrderedDict(old=(old, 'prepend'))

        # We now update the composer.
        composer_method_name = specifiers[1]
        composer_method = getattr(composer, composer_method_name)
        if composer_method_name in ('add_before', 'add_after'):
            composer_method(specifiers[2], specifiers[0], func)
        elif composer_method_name == 'remove':
            composer_method(specifiers[0])
        else:
            composer_method(specifiers[0], func)

        # Finally we update the _customs dict and reassign the composer.
        setattr(self, method_name, composer)
        if not internal:
            customs = self._customs[method_name]
            if composer_method_name == 'remove':
                del customs[specifiers[0]]
            elif composer_method_name == 'replace':
                if specifiers[0] in customs:
                    old = list(customs[specifiers[0]])
                    old[0] = func
                    customs[specifiers[0]] = tuple(old)
                else:
                    ind = composer._names.index(specifiers[0])
                    if ind == 0:
                        customs[specifiers[0]] = (func, 'prepend')
                    else:
                        n = composer._names[ind-1]
                        customs[specifiers[0]] = (func, 'add_after', n)
            else:
                op = [func] + list(specifiers[1:])
                self._customs[method_name][specifiers[0]] = tuple(op)

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
        # Loop on methods which are affected by mofifiers.
        for meth_name, modifiers in obj._customs.items():
            if isinstance(modifiers, MethodType):
                self.modify_behavior(meth_name, modifiers)
                continue

            # Loop through all the modifications.
            for custom, modifier in modifiers.items():

                method = getattr(self, meth_name)
                # In the absence of anchor we simply attempt the operation.
                if modifier[1] not in ('add_after', 'add_before'):
                    self.modify_behavior(meth_name, modifier[0],
                                         (custom, modifier[1]))
                elif not isinstance(method, MethodComposer):
                    aux = {'add_after': 'append', 'add_before': 'prepend'}
                    self.modify_behavior(meth_name, modifier[0],
                                         (custom, aux[modifier[1]]))

                # Otherwise we check whether or not the anchor exists and if
                # not try to find the most meaningfull one.
                else:
                    our_names = method._names
                    if modifier[2] in our_names:
                        self.modify_behavior(meth_name, modifier[0],
                                             (custom, modifier[1],
                                              modifier[2]))
                    else:
                        feat_names = getattr(obj, meth_name)._names
                        # For add after we try to find an entry existing in
                        # both feature going backward (we will prepend at the
                        # worst), for add before we go forward (we will append
                        # in the absence of match).
                        shift = -1 if modifier[1] == 'add_after' else -1
                        index = feat_names.index(custom)
                        while index > 0 and index < len(feat_names)-1:
                            index += shift
                            name = feat_names[index]
                            if name in our_names:
                                self.modify_behavior(meth_name, modifier[0],
                                                     (custom, modifier[1],
                                                      name))
                                shift = 0
                                break

                        if shift != 0:
                            op = 'prepend' if shift == -1 else 'append'
                            self.modify_behavior(meth_name, modifier[0],
                                                 (custom, op))
