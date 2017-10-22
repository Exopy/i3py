# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base class for instrument channels.

"""
from .base_subsystem import SubSystem
from .abstracts import (AbstractChannel, AbstractChannelContainer,
                        AbstractChannelDescriptor)
from .utils import check_options


class ChannelContainer(AbstractChannelContainer):
    """Default container storing references to the instrument channels.

    Note that is the responsability of the user to check that a channel is
    available before querying it.

    Parameters
    ----------
    cls : class
        Class of the channel to instantiate when a channel is requested.

    parent : HasFeatures
        Reference to the parent object holding the channel.

    name : unicode
        Name of the channel subpart on the parent.

    list_available : callable
        Function to call to query the list of available channels.

    aliases : dict
        Dict mapping aliases names to the real channel id to use.

    """

    def __init__(self, cls, parent, name, list_available, aliases):
        self._cls = cls
        self._channels = {}
        self._name = name
        self._parent = parent
        self._aliases = aliases
        self._list = list_available

    @property
    def available(self):
        """List the available channels.

        """
        return self._list(self._parent)

    @property
    def aliases(self):
        """List the aliases.

        """
        return self._aliases.copy()

    def __getitem__(self, ch_id):
        if ch_id in self._aliases:
            ch_id = self._aliases[ch_id]

        if ch_id in self._channels:
            return self._channels[ch_id]

        parent = self._parent
        ch = self._cls(parent, ch_id,
                       caching_allowed=parent.use_cache
                       )
        self._channels[ch_id] = ch
        return ch

    def __iter__(self):
        for id in self.available:
            yield self[id]


class Channel(SubSystem):
    """Channels are used to represent instrument channels identified by a id
    (a number generally).

    They are similar to SubSystems in that they expose a part of the
    instrument capabilities but multiple instances of the same channel
    can exist at the same time under the condition that they have different
    ids.

    By default channels passes their id to their parent when they call
    default_*_feat as the kwarg 'ch_id' which can be used by the parent
    to direct the call to the right channel.

    Parameters
    ----------
    parent : HasFeat
        Parent object which can be the concrete driver or a subsystem or
        channel.
    id :
        Id of the channel used by the instrument to correctly route the calls.

    Attributes
    ----------
    id :
        Id of the channel used by the instrument to correctly route the calls.

    """
    def __init__(self, parent, id, **kwargs):
        super(Channel, self).__init__(parent, **kwargs)
        self.id = id

    def default_get_feature(self, feat, cmd, *args, **kwargs):
        """Channels simply pipes the call to their parent.

        """
        kwargs['id'] = self.id
        return self.parent.default_get_feature(feat, cmd, *args, **kwargs)

    def default_set_feature(self, feat, cmd, *args, **kwargs):
        """Channels simply pipes the call to their parent.

        """
        kwargs['id'] = self.id
        return self.parent.default_set_feature(feat, cmd, *args, **kwargs)

    def default_check_operation(self, feat, value, i_value, response):
        """Channels simply pipes the call to their parent.

        """
        return self.parent.default_check_operation(feat, value, i_value,
                                                   response)


AbstractChannel.register(Channel)


class ChannelDescriptor(object):
    """Descriptor giving access to a channel container.

    The channel container is returned only if the proper conditions are matched
    in terms of static options (as specified through the options of the
    channel declarator).

    """
    __slots__ = ('cls', 'name', 'options', 'container', 'list_available',
                 'aliases')

    def __init__(self, cls, name, options, container, list_available, aliases):
        self.cls = cls
        self.name = name
        self.options = options
        self.container = container
        self.list_available = list_available
        self.aliases = aliases

    def __get__(self, instance, cls):
        if instance is None:
            return self.cls
        else:
            if self.name not in instance._channel_container_instances:
                if self.options:
                    test, msg = check_options(instance, self.options)
                    if not test:
                        ex_msg = ('%s is not accessible with instrument '
                                  'options: %s')
                        raise AttributeError(ex_msg % (self.name, msg))

                cc = self.container(cls, instance, self.name,
                                    self.list_available, self.aliases)
                instance._channel_container_instances[self.name] = cc

            return instance._channel_container_instances[self.name]


AbstractChannelDescriptor.register(ChannelDescriptor)
