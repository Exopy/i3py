# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Common functionalities.

"""
import logging
import re
from string import Formatter
from io import StringIO

from pyvisa import logger

logger = logging.LoggerAdapter(logger, {'backend': 'i3py-sim'})

_FORMATTER = Formatter()


class NamedObject(object):
    """A class to construct named sentinels.

    """
    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<%s>' % self.name

    __str__ = __repr__


def iter_bytes(data, mask, send_end):
    for d in data[:-1]:
        yield bytes([d & ~mask])

    if send_end:
        yield bytes([data[-1] | ~mask])
    else:
        yield bytes([data[-1] & ~mask])

int_to_byte = lambda val: bytes([val])
last_int = lambda val: val[-1]


def build_matcher(query, optional=False):
    """Build a regular expression matching a query no matter the arguments.

    """
    matcher = StringIO()
    pattern = '\S*' if optional else '\S+'
    for literal, field, fmt, conv in _FORMATTER.parse(query):
        matcher.write(re.escape(literal))
        if field is not None:
            matcher.write(pattern)
    return matcher.getvalue()


def build_scpi_matcher(query, optional=False):
    """Build a regular expression allowing to match a scpi command.

    This takes into account the fact that lowercase characters are optional,
    and character between brackets are also optional.

    """
    matcher = StringIO()
    iter_query = iter(query)
    for c in iter_query:

        # Put lower characters as optional.
        # TODO in full SCPI any number of character can be specified
        if c.islower():
            sub_query = StringIO()
            sub_query.write(c)
            while True:
                c = next(iter_query)
                if not c.islower():
                    break
                sub_query.write(c)
            matcher.write('(?' + sub_query.getvalue() + ')')
            # c is now the next character so go on as usual.

        # If we find an optional area delimiter make the content optional.
        if c == '[':
            sub_query = StringIO()
            while True:
                c = next(iter_query)
                if c == ']':
                    break
                sub_query.write(c)
            sub_match = build_scpi_matcher(sub_query.getvalue())
            matcher.write('(?' + sub_match + ')')
        else:
            matcher.write(c)

    return build_matcher(matcher.getvalue(), optional)
