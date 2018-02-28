# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Action-like method wrapper describing a dialog.

"""
from string import Formatter

from i3py.core.actions import Action

from .component import NoResponse, NoMatch
from .exceptions import I3pyVisaSimException


def _chain_getattr(obj, attr_chain):
    """Access an attribute by chaining getattr calls.

    """
    if not attr_chain:
        return obj

    return _chain_getattr(getattr(obj, attr_chain[0]), attr_chain[1:])


def build_answer_formatter(format_answer):
    """Build a function grabbing the driver attibute and format an answer.

    """
    attrs = [field[1].split('.') for field in Formatter().parse(format_answer)
             if field[1] is not None]

    def answer(driver):
        """Grab the driver attribute using getattr and format the answer.

        """
        values = {k: _chain_getattr(driver, k) for k in attrs}
        return format_answer.format(**values)


class Dialog(Action):
    """Method decorator describing an instrument dialog.

    If parameters can be passed to the instrument formatted in the query,
    if will be extracted from the query and passed to the decorated function.
    The function should return a text message or None depending on whether the
    command should lead to an answer.

    Parameters
    ----------
    cmd : str or Parser
        String or stringparser.Parser to use to extract the interesting value
        from the instrument answer.

    format_answer : str, optional
        String format describing the instrument answer. Each field should have
        a name matching an attribute on the component on which the

    Other parameters are the ones of Action.

    """
    def __init__(self, cmd, answer_format=None, **kwargs):
        super(Dialog, self).__init__(**kwargs)
        # Passed command.
        self.cmd = cmd
        self.kwargs.update(cmd=cmd, answer_format=answer_format)

        # Regular expression used to match the query so that an error in the
        # value does not prevent a match. Its value is set by the framework
        # when the parent component class is finalized.
        self._matcher = None  # re.compile('^' + build_matcher(cmd) + '$')

        # Parser used to extract the arguments of the command. Its value is set
        # by the framework when the parent component class is finalized.
        self._parser = None

        # If answer_format is specified build a simple function formatting the
        # answer.
        if answer_format:
            self(build_answer_formatter(answer_format))

    def build_matcher(self, builder, options):
        """Build the matcher for the command using the provided function.

        """
        pass  # XXX implement, need also to implement proper parsing for SCPI

    def match(self, driver, query):
        """Try to match the query and extract the parameters.

        Parameters
        ----------
        query : unicode
            Query on which to try to match the dialog command.

        """
        if self._matcher.match(query):

            # Parsing the query can return either:
            # - an empty didt if no matching field exists in the cmd
            # - a single Python object if there is a single field
            # - a list or dict for multiple matching fields
            try:
                args = self._parser(query)
            except ValueError as e:
                driver.handle_error(e)

            if isinstance(args, list):
                args = args
                kwargs = {}
            elif isinstance(args, dict):
                args = ()
                kwargs = args
            else:
                args = (args,)
                kwargs = {}

            try:
                response = getattr(driver, self.name)(*args, **kwargs)
            except I3pyVisaSimException as e:
                driver.handle_error(e)

            return response or NoResponse
        else:
            return NoMatch
