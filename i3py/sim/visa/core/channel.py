# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Channels implementation for simulated instruments.

"""
import re

from stringparser import Parser
from i3py.core.base_channel import ChannelContainer, Channel

from .component import BaseComponentMixin, NoMatch, ErrorOccured


class SimulatedChannelsContainer(ChannelContainer):
    """Container for channels of simulated instruments.

    """
    def __init__(self, cls, parent, name, part):
        super(SimulatedChannelsContainer, self).__init__(cls, parent, name,
                                                         part)
        self._selectable_ = part._selectable_
        self._optional_inline_ = False
        self._available = []
        # Store a reference to the currently selected channel
        self._selected = None
        # XXX build matcher at init and retrieve scpi and case senitivity from root
        if part._cmd_:
            # Allow to add formatting informations.
            if '{ch_id' in part._cmd_:
                # Use $ sign to signal an optional inline selection. In this
                # case the channel must be declared selectable.
                optional_ch = '${ch_id' in part._cmd_
                if optional_ch and not self._selectable_:
                    raise ValueError('A channel with optional selection in '
                                     'the command string must be selectable.')
                self._optional_inline_ = optional_ch
                # Regular expression used to match the query so that an error
                # in the value does not prevent a match.
                cmd = '^' + build_matcher(part._cmd_, optional_ch)
                # The parser will extract the selection. If optional the error
                # will be caught and the previoulsy selected channel will be
                # used.
                self._parser = Parser(part._cmd_)
            else:
                cmd = '^' + part._cmd_
                self._parser = None
            self._matcher = re.compile(cmd)
        elif self._selectable_:
            self._matcher = None
        else:
            raise ValueError('A channel must either be selectable or the '
                             'channel must be extractable from the command '
                             'string.')

    def match(self, driver, query):
        """Try to find a match for a query in the channel commands.

        """
        if self._matcher is not None:
            match = self._matcher.match(query)
            if not match:
                return NoMatch
            query = match.string[match.end():]
            if self._parser:
                try:
                    parsed = self._parser(match.string[:match.end()])
                except ValueError as e:
                    if self._optional_inline_:
                        parsed = {'ch_id': self.selected}
                    else:
                        driver.handle_error(e)
                        return ErrorOccured
                self.selected = parsed['ch_id']

        if self._selected is None:
            raise RuntimeError('No channel was previously selected')

        return self._selected.match(driver, query)

    @property
    def selected(self):
        """Id of the currently selected channel.

        Reading and writing this value make sense only if the channel is
        selectable.

        """
        if self._selected is None:
            return None
        return self._selected.id

    @selected.setattr
    def selected(self, value):
        self._selected = self[value]

    @property
    def available(self):
        """Access the tuple of available channels.

        """
        return self._available

    @available.setter
    def available(self, value):
        self._available = tuple(value)
        for id_ in value:
            if id_ not in self._channels:
                del self._channels[id_]

# XXX Call parent implementation
class SimulatedChannel(BaseComponentMixin, Channel):
    """A component representing a device channels.

    """
    def handle_error(self, exception):
        """
        """
        pass
