# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Implements base classes for instrumentation related exceptions.

They are useful to mix with specific exceptions from libraries or modules and
therefore allowing code to catch them via i3py excepts without breaking
specific ones.

"""


class I3pyError(Exception):
    """Base class for all I3py errors.

    """
    pass


class I3pyInvalidCommand(I3pyError):
    pass


class I3pyTimeoutError(I3pyError):
    pass


class I3pyInterfaceNotSupported(I3pyError):
    pass
