# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base classes for simulated instrument components.

"""
from i3py.core import HasFeature, Subsystem

from .features import SimulatedFeature
from .dialog import Dialog
from .common import NamedObject


def to_bytes(val):
    """Takes a text message and return an encoded version.

    """
    if val is NoResponse:
        return val
    val = val.replace('\\r', '\r').replace('\\n', '\n')
    return val.encode()


#: Sentinel used for when there is no match.
NoMatch = NamedObject(name='NoMatch')


#: Sentinel used for when there should not be a response to a query
NoResponse = NamedObject(name='NoResponse')


#: Sentinel marking that the available channels should be specified by the user
UserSpecifiedChannels = NamedObject('UserSpecifiedChannels')


class BaseComponentMixin(HasFeature):
    """Base mixin class for simulated instrument components.

    """

    @classmethod
    def build_matchers(cls, builder, options):
        """Build the matchers of all the features/dialogs/components.

        """
        for f in cls.__features__.values():
            f.build_matcher(builder, options)

        for a in cls.__actions__.values():
            a.build_matcher(builder, options)

        for s in cls.__subsystems__.values():
            s.build_matchers(builder, options)

        for c in cls.__channels__.values():
            c.build_matchers(builder, options)

    @classmethod
    def collect_error_handlers(cls, root):
        """Collect all declared error handlers.

        Parameters
        ----------
        root : Device
            Root component repsonsible for error management.

        """
        pass

    def _match_(self, query):
        """Try to find a match for a query in the instrument commands.

        """
        for f in [f for f in dir(type(self))
                  if isinstance(f, (SimulatedFeature, Dialog))]:
            response = f.match(self, query)
            if response is not NoMatch:
                return response

        for s in self.__subsystems__:
            response = s._match_(query)
            if response is not NoMatch:
                return response

        for c in self.__channels__:
            response = c._match_(query)
            if response is not NoMatch:
                return response

        return NoMatch

    def handle_error(self, exception):
        """Simply pass the exception up to the parent.

        The root device is responsible for handling the errors that buble up
        to him.

        """
        self.parent.handle_error(exception)


class Component(BaseComponentMixin, Subsystem):
    """Subcomponent for a simulated instrument.

    If the _cmd_ class attribute is set it will be stripped from the analysed
    query.

    """
    def _match_(self, query):
        """Analyse whether the query fits any known query.

        """
        if getattr(self, '_cmd_', None):
            match = self._matcher.match(query)
            if match:
                query = query[match.end():]
                return super(Component, self).match(query)
            else:
                bypass = getattr(self, '_bypass_', [])
                for b in bypass:
                    response = b.match(self, query)
                    if response is not NoMatch:
                        return response
                return NoResponse

        else:
            return super(Component, self).match(query)
