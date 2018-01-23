# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base classes for simulated instrument components.

"""
from i3py.core import HasFeature, Subsystem, subsystem, channel

from .features import SimulatedFeature
from .dialog import Dialog
from .common import NamedObject, build_matcher, build_scpi_matcher


def to_bytes(val):
    """Takes a text message and return an encoded version.

    """
    if val is NoResponse:
        return val
    val = val.replace('\\r', '\r').replace('\\n', '\n')
    return val.encode()


# Sentinel used for when there is no match.
NoMatch = NamedObject(name='NoMatch')


# Sentinel used for when there should not be a response to a query
NoResponse = NamedObject(name='NoResponse')


#
ErrorOccurred = NamedObject(name='ErrorOccured')


# Sentinel marking that the available channels should be specified by the user.
UserSpecifiedChannels = NamedObject('UserSpecifiedChannels')


class BaseComponentMixin(HasFeature):
    """Base mixin class for simulated instrument components.

    """
    def match(self, query):
        """Try to find a match for a query in the instrument commands.

        """
        for f in [f for f in dir(type(self))
                  if isinstance(f, (SimulatedFeature, Dialog))]:
            response = f.match(self, query)
            if response is not NoMatch:
                return response

        for s in self.__subsystems__:
            response = s.match(query)
            if response is not NoMatch:
                return response

        for c in self.__channels__:
            response = c.match(query)
            if response is not NoMatch:
                return response

        return NoMatch

    def handle_error(self, exception):
        """
        """
        raise NotImplementedError()

    @classmethod
    def finalize_cls_creation(cls):
        """
        """
        pass


class Component(BaseComponentMixin, Subsystem):
    """Subcomponent for a simulated instrument.

    If the _cmd_ class attribute is set it will be stripped from the analysed
    query.

    """
    # XXX build matcher at init and retrieve scpi and case senitivity from root
    @classmethod
    def finalize_cls_creation():
        """
        """
        pass

    def match(self, query):
        """Analyse whether the query fits any known query.

        """
        if getattr(self, '_cmd_', None):
            if query.startswith(self._cmd_):
                query = query.strip(self._cmd_)
                return super(Component, self).match(query)
            else:
                return NoResponse

        else:
            return super(Component, self).match(query)

    # XXX call parent, rebuild full query perhaps
    def handle_error(self, error):
        """
        """
        pass


class component(subsystem):
    """Sentinel used to collect declarations for a subcomponent.

    Parameters
    ----------
    cmd : unicode, optional
        Prefix for all commands of the subsystem.

    bases : class or tuple of classes, optional
        Class or classes to use as base class when no matching subpart exists
        on the driver.

    """
    def __init__(self, cmd='', use_scpi=None, bases=()):

        super(component, self).__init__(bases)
        if cmd:
            self._cmd_ = cmd


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
                 bases=(), aliases=None, container_type=None):
        if container_type is None:
            from .channel import SimulatedChannelContainer
            container_type = SimulatedChannelContainer
        super(component_channel, self).__init__(available, bases, aliases,
                                                container_type)
        self._cmd_ = cmd
        self._selectable_ = selectable
        # In simulated instruments the available channels can be specified
        # when the simulated instrument is initialized.
        if available is None:
            self._available_ = UserSpecifiedChannels
