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


class I3pyFailedGet(I3pyError):
    """Error raised when getting an instrument feature value failed.

    """
    pass


class I3pyFailedSet(I3pyError):
    """Error raised when setting an instrument feature value failed.

    """
    pass


class I3pyFailedCall(I3pyError):
    """Error raised when calling an action fails.

    """
    pass


class I3pyValueError(ValueError, I3pyError):
    """I3py specific value error.

    """
    pass


class I3pyLimitsError(ValueError, I3pyError):
    """Error raised when a value does not fit in the given limits.

    """
    pass
