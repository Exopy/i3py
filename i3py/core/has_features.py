# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""HasFeatures is the most basic object in I3py.

It handles the use of Features, Subsystem, and Channel and the possibility
to customize Feature behaviour by defining specially named methods.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import logging
from inspect import getsourcelines
from itertools import chain
from abc import ABCMeta
from collections import defaultdict

from future.utils import with_metaclass

from .abstracts import (AbstractHasFeatures, AbstractFeature, AbstractAction,
                        AbstractMethodCustomizer)
from .declarative import (set_feat, set_action, SubpartDecl, subsystem,
                          channel, limit)


class HasFeaturesMeta(ABCMeta):
    """ Metaclass handling Feature customisation, subsystems registration...

    """
    def __new__(meta, name, bases, dct):
        # Pass over the class dict once and collect the information
        # necessary to implement the various behaviours.
        feats = {}                       # Feature declarations
        actions = {}                     # Action declarations
        subsystems = {}                  # Subsystem declarations
        channels = {}                    # Channels declaration
        subparts = {}                    # Declared subparts
        feat_paras = {}                  # Sentinels changing feats behavior.
        action_paras = {}                # Sentinels changing actions behavior.
        m_customizers = {}               # Sentinels customizing methods.
        limits = {}                      # Defined limits.

        docs = dct.pop('_docs_') if '_docs_' in dct else None

        # First we identify all subparts and keep only keys which are not
        # knwown aliases.
        subparts = {k: v for k, v in dct.items()
                    if isinstance(v, SubpartDecl) and k not in v._aliases_}
        # Then we clean the namespace
        for s_name, subpart in subparts.items():
            subpart._name_ = s_name
            subparts[s_name] = subpart
            subpart.clean_namespace(dct)

        # Names that should be removed from the class body
        to_remove = set()

        # Next we identify all other elements in the passed dict to clean it up
        # before creating the class.
        for key, value in dct.items():

            if isinstance(value, AbstractFeature):
                feats[key] = value
                value.name = key

            elif isinstance(value, AbstractAction):
                actions[key] = value
                value.name = name

            elif isinstance(value, set_feat):
                feat_paras[key] = value

            elif isinstance(value, set_action):
                action_paras[key] = value

            elif isinstance(value, AbstractMethodCustomizer):
                m_customizers[key] = value

            elif isinstance(value, limit):
                to_remove.add(key)
                limit_id = value.name
                limits[limit_id] = value.func

        # Clean up class dictionary.
        for k in chain(feat_paras, action_paras, m_customizers, to_remove):
            del dct[k]

        # Create the class object.
        cls = super(HasFeaturesMeta, meta).__new__(meta, name, bases, dct)

        # Purge the list of base classes (for the most base class object is
        # present)
        bases = [b for b in bases if issubclass(b, AbstractHasFeatures)]

        # Analyse the source code to find the doc for the defined Features.
        # This will work as long as two subpart are not aliased in the same
        # way which is probabbly good enough.
        if docs is None:
            docs = {}
            try:
                lines, _ = getsourcelines(cls)
            except OSError:
                msg = 'Failed to retrieve source lines for %s.' % cls
                logging.getLogger(__name__).warn(msg)
            else:
                doc = ''
                for line in lines:
                    l = line.strip()
                    if l.startswith('#:'):
                        doc += ' ' + l[2:].strip()
                    elif ' = ' in l:
                        attr_name = l.split(' = ', 1)[0]
                        docs[attr_name] = doc.strip()
                        doc = ''

        # Make the feature build their docs from the provided docstrings.
        for f in feats:
            if f in docs:
                feats[f].make_doc(docs[f])

        # Handle the subparts by creating dynamic subclasses.
        inherited_ss = dict([(k, v) for b in bases
                             for k, v in b.__subsystems__.items()])
        inherited_ch = dict([(k, v) for b in bases
                             for k, v in b.__channels__.items()])

        # Create subsystem and channels classes
        for part_name, part in subparts.items():
            if not hasattr(part, 'retries_exceptions'):
                part.retries_exceptions = cls.retries_exceptions
            # If a subpart with the same name has already been declared on a
            # parent class we use its class as a base class for the one we are
            # about to create.
            if part_name in inherited_ss:
                subsystems[part_name] = part.build_cls(name,
                                                       inherited_ss[part_name],
                                                       docs)
            elif part_name in inherited_ch:
                ch_cls = part.build_cls(name, inherited_ch[part_name],
                                        docs)

                # Must be valid otherwise parent declaration would be messed up
                inherited_part = inherited_ch[part_name]._part_
                part._available_ = (part._available_ or
                                    inherited_part._available_)
                part._ch_aliases_ = (part._ch_aliases_ or
                                     inherited_part._ch_aliases_)
                channels[part_name] = ch_cls

            else:
                if isinstance(part, subsystem):
                    subsystems[part_name] = part.build_cls(name, None,
                                                           docs)
                elif isinstance(part, channel):
                    ch_cls = part.build_cls(name, None, docs)
                    if not part._available_:
                        msg = 'No way to identify available channels for {}'
                        raise ValueError(msg.format(part_name))
                    channels[part_name] = ch_cls

        # Put references to the subsystem and channel classes on the class.
        for k, v in subsystems.items():
            setattr(cls, k, v)
        for k, v in channels.items():
            setattr(cls, k, v)

        inherited_ss.update(subsystems)
        subsystems = inherited_ss
        inherited_ch.update(channels)
        channels = inherited_ch

        # Customize feature (action) for which a set_feat (set_action) has been
        # declared.
        # This creates a new instance which is hence owned.
        for paras, owned in ((feat_paras, feats), (action_paras, actions)):
            for k, v in paras.items():
                new = v.customize(getattr(cls, k))
                owned[k] = new
                setattr(cls, k, new)

        # Walk the mro of the class, excluding itself, in reverse order
        # collecting all of the features and actions into a single dict. The
        # reverse update preserves the mro of overridden features and actions.
        base_feats = {}
        base_actions = {}
        for base in reversed(cls.__mro__[1:]):
            if base is not AbstractHasFeatures \
                    and issubclass(base, AbstractHasFeatures):
                base_feats.update(base.__feats__)
                base_actions.update(base.__actions__)

        # Clone all features/actions not owned at this stage and keep a
        # reference to it in the proper dict.
        for base, owned in ((base_feats, feats), (base_actions, actions)):
            for k, v in ((k, v) for k, v in base.items() if k not in owned):
                clone = v.clone()
                setattr(cls, k, clone)
                owned[k] = clone

        # Add the special statically defined behaviours for the
        # features/actions.
        for key, cust in m_customizers.items():
            cust.customize(cls, key)

        # Put a reference to the features dict on the class.
        cls.__feats__ = feats

        # Put a reference to the actions dict on the class.
        cls.__actions__ = actions

        # Put a reference to the subsystems in the class.
        # This is used at initialisation to create the appropriate subsystems
        cls.__subsystems__ = subsystems

        # Put a reference to the (channel, part) pairs in the class
        cls.__channels__ = channels

        # Put a reference to the limits in the class.
        cls.__limits__ = limits

        return cls


class HasFeatures(with_metaclass(HasFeaturesMeta, object)):
    """Base class for objects using the Features mechanisms.

    """
    #: Tuple of exception to consider when securing a communication (either via
    #: secure_communication decorator or for features with a non zero
    #: retries value)
    retries_exceptions = ()

    def __init__(self, caching_allowed=True):

        self._cache = {}
        self._limits_cache = {}

        subsystems = self.__subsystems__
        channels = self.__channels__

        self.use_cache = caching_allowed

        # Initializing subsystems.
        for ss, cls in subsystems.items():
            subsystem = cls(self, caching_allowed=caching_allowed)
            setattr(self, ss, subsystem)

        # Creating a channel container for each kind of declared channels.
        for ch, cls in channels.items():
            listing_function = cls._part_.build_list_channel_function()
            ch_holder = cls._container_type_(cls, self, ch, listing_function,
                                             cls._part_._ch_aliases_)
            setattr(self, ch, ch_holder)

    def get_feat(self, name):
        """ Acces the feature matching the given name.

        Parameters
        ----------
        name : unicode
            Name of the Feature to be retrieved

        Returns
        -------
        feat : Feature
            Matching Feature object

        """
        return getattr(self.__class__, name)

    def clear_cache(self, subsystems=True, channels=True, features=None):
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
        cache = self._cache
        if features:
            par = list()
            sss = defaultdict(list)
            chs = defaultdict(list)
            for name in features:
                if '.' in name:
                    aux, n = name.split('.', 1)
                    if not aux:
                        par.append(n)
                    elif aux in self.__subsystems__:
                        sss[aux].append(n)
                    else:
                        chs[aux].append(n)
                elif name in cache:
                    del cache[name]

            if par:
                self.parent.clear_cache(features=par)

            for ss in sss:
                getattr(self, ss).clear_cache(features=sss[ss])

            if self.__channels__:
                for ch in chs:
                    for o in getattr(self, ch):
                        o.clear_cache(features=chs[ch])
        else:
            self._cache = {}
            if subsystems:
                for ss in self.__subsystems__:
                    getattr(self, ss).clear_cache(channels=channels)
            if channels and self.__channels__:
                for chs in self.__channels__:
                    for ch in getattr(self, chs):
                        ch.clear_cache(subsystems)

    def check_cache(self, subsystems=True, channels=True, features=None):
        """Return the value of the cache of the object.

        The cache values for the subsystems and channels are not accessible.

        Parameters
        ----------
        subsystems : bool, optional
            Whether or not to include the subsystems caches. This argument is
            used only if properties is None.
        channels : bool, optional
            Whether or not to include the channels caches. This argument is
            used only if properties is None.
        features : iterable of str, optional
            Name of the features whose cache should be cleared. All caches
            will be cleared if not specified.

        Returns
        -------
        cache : dict
            Dict containing the cached value, if the properties arg is given
            None will be returned for the field with no cached value.

        """
        cache = {}
        if features:
            sss = defaultdict(list)
            chs = defaultdict(list)
            for name in features:
                if '.' in name:
                    aux, n = name.split('.', 1)
                    if aux in self.__subsystems__:
                        sss[aux].append(n)
                    else:
                        chs[aux].append(n)
                elif name in self._cache:
                    cache[name] = self._cache[name]

            for ss in sss:
                cache[ss] = getattr(self, ss).check_cache(features=sss[ss])

            if self.__channels__:
                for ch in chs:
                    ch_cache = {}
                    cache[ch] = ch_cache
                    channel_cont = getattr(self, ch)
                    for ch_id in channel_cont.available:
                        chan = channel_cont[ch_id]
                        ch_cache[ch_id] = chan.check_cache(features=chs[ch])
        else:
            cache = self._cache.copy()
            if subsystems:
                for ss in self.__subsystems__:
                    cache[ss] = getattr(self, ss)._cache.copy()

            if channels:
                for chs in self.__channels__:
                    ch_cache = {}
                    cache[chs] = ch_cache
                    channel_cont = getattr(self, chs)
                    for ch in channel_cont.available:
                        ch_cache[ch] = channel_cont[ch]._cache.copy()

        return cache

    @property
    def declared_limits(self):
        """Set of declared limits for the class.

        Limits are considered declared as soon as a getter has been defined.

        """
        return list(self.__limits__)

    def get_limits(self, limits_id):
        """Access the limits object matching the definition.

        Parameters
        ----------
        limits_id : str
            Id of the limits to retrieve. The id should be the name of the
            limits.

        Returns
        -------
        limits_validator: AbstractLimitsValidator
            A limits validator matching the current attributes state, which can
            be used to validate values.

        """
        if limits_id not in self._limits_cache:
            self._limits_cache[limits_id] = self.__limits__[limits_id](self)

        return self._limits_cache[limits_id]

    def discard_limits(self, limits_id):
        """Remove a limits from the cache.

        This is called when a Feature declare a limits key in the discard dict.

        Parameters
        ----------
        limits_id : iterable
            Iterable of the ids of the limits to discard.

        """
        for lim_id in limits_id:
            if lim_id in self._limits_cache:
                del self._limits_cache[lim_id]

    def reopen_connection(self):
        """Reopen the connection to the instrument.

        """
        raise NotImplementedError()

    def default_get_feature(self, feat, cmd, *args, **kwargs):
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
        raise NotImplementedError()

    def default_set_feature(self, feat, cmd, *args, **kwargs):
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
        raise NotImplementedError()

    def default_check_operation(self, feat, value, i_value, state=None):
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
        raise NotImplementedError()


AbstractHasFeatures.register(HasFeatures)
