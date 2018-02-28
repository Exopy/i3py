# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Additional declarative component used to declare simulated visa drivers.

"""
from i3py.core import subsystem, channel
from i3py.core.abstracts import AbstractSubSystem, AbstractChannel

from .common import NamedObject


#: Sentinel marking that the available channels should be specified by the user
UserSpecifiedChannels = NamedObject('UserSpecifiedChannels')


class component(subsystem):
    """Sentinel used to collect declarations for a subcomponent.

    Parameters
    ----------
    cmd : unicode, optional
        Prefix for all commands of the subsystem.

    bypass : list, optional
        List of features/actions/components that may match even though the
        component did not match.

    bases : class or tuple of classes, optional
        Class or classes to use as base class when no matching subpart exists
        on the driver.

    """
    def __init__(self, cmd='', bypass=None, bases=(), checks='', options=None,
                 descriptor_type=None):

        super().__init__(bases, checks, options, descriptor_type)
        # Those attributes can be accessed from the _declaration_ attribute
        # set on the class.
        if cmd:
            self._cmd_ = cmd
            if self.bypass:
                self._bypass_ = bypass

    def compute_base_classes(self):
        """Add SubSystem in the base classes if necessary.

        The first class should always be a SubSystem subclass so prepend if it
        is not so.

        """
        bases = self._bases_
        if not bases or not issubclass(bases[0], AbstractSubSystem):
            from .component import Component
            bases = (Component,) + bases

        return bases


class component_channel(channel):
    """Sentinel used to collect declarations or modifications for a channel.

    Parameters
    ----------
    cmd : unicode, optional
        Prefix for all commands of the channel. This may include fields to
        extract to identify the channel.

    available : tuple or list, optional
        List of channel ids. This should only be specified if the channels of
        an instrument are static.

    selectable : bool, optional
        Can the channel be selected and remembered (all following commands
        hence being directed to the selected channel).

    bases : class or tuple of classes, optional
        Class or classes to use as base class when no matching subpart exists
        on the driver.

    aliases : dict, optional
        Dictionary providing aliases for channels ids. Aliases can be simple
        values, list or tuple.

    container_type : type, optional
        Container type to use to store channels.

    """
    def __init__(self, cmd='', available=None, selectable=False,
                 bases=(), aliases=None, container_type=None, options=None,
                 checks=None,  descriptor_type=None):
        super().__init__(available, bases, aliases, container_type, options,
                         checks, descriptor_type)
        # Those attributes can be accessed from the _declaration_ attribute
        # set on the class.
        self._cmd_ = cmd
        self._selectable_ = selectable

        # In simulated instruments the available channels can be specified
        # when the simulated instrument is initialized.
        if available is None:
            self._available_ = UserSpecifiedChannels

    def compute_base_classes(self):
        """Add Channel in the base classes if necessary.

        The first class should always be a Channel subclass so prepend if it
        is not so.

        """
        bases = self._bases_
        if not bases or not issubclass(bases[0], AbstractChannel):
            from .channel import SimulatedChannel
            bases = (SimulatedChannel,) + (bases)
        return bases

    def build_list_channel_function(self):
        """Build the function used to list the available channels.

        """
        if self._available_ is UserSpecifiedChannels:
            # XXX define a way to get the user specified ids
            pass
        elif isinstance(self._available_, (tuple, list)):
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
            from .channel import SimulatedChannelsContainer
            ctn_type = SimulatedChannelsContainer
        else:
            ctn_type = self._container_type_

        list_func = self.build_list_channel_function()
        return dsc_type(cls, name, self._options_, ctn_type, list_func,
                        self._ch_aliases_)
