# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""BaseInstrument defines the common expected interface for all drivers.

"""
from threading import RLock
from weakref import WeakKeyDictionary, WeakValueDictionary
from textwrap import fill
from inspect import cleandoc

from .abstracts import AbstractBaseDriver
from .errors import I3pyTimeoutError
from .has_features import HasFeatures


class InstrumentSigleton(type):
    """Metaclass ensuring that a single driver is created per instrument.

    """

    _instances_cache = WeakKeyDictionary

    def __call__(cls, *args, **kwargs):
        # This is done on first call rather than init to avoid useless memory
        # allocation.
        if cls not in cls._instances_cache:
            cls._instances_cache[cls] = WeakValueDictionary()

        cache = cls._instances_cache[cls]
        driver_id = cls.compute_id(args, kwargs)
        if driver_id not in cache:
            dr = super(InstrumentSigleton, cls).__call__(*args, **kwargs)

            cache[driver_id] = dr
        else:
            dr = cache[driver_id]
            dr.newly_created = False

        return dr


class BaseDriver(HasFeatures, metaclass=InstrumentSigleton):
    """ Base class of all instrument drivers in I3py.

    This class defines the common interface drivers are expected to implement
    and take care of keeping a single instance for each set of connection
    informations.

    WARNING: The optional arguments will be taken into account only if the
    instance corresponding to the connection infos does not exist.

    Parameters
    ----------
    connection_info : dict
        Dict containing all the necessary information to open a connection to
        the instrument
    caching_allowed : bool, optionnal
        Boolean use to determine if instrument properties can be cached

    Attributes
    ----------
    secure_com_except : tuple
        Class attributes used to determine which errors to take into account
        when securing a communication.

    """
    secure_com_except = (I3pyTimeoutError,)

    def __init__(self, *args, **kwargs):
        super(BaseDriver, self).__init__(kwargs.get('caching_allowed', True))

        self.owner = ''
        self.newly_created = True
        self.lock = RLock()

    @classmethod
    def compute_id(cls, args, kwargs):
        """Use the arguments to compute a unique id for the instrument.

        This can also be used to alter the content of the kwargs dictionary.
        This is why we do not unpack it.

        Parameters
        ----------
        args :
            Positional arguments passed to the constructor

        kwargs :
            Keyword arguments passed to the constructor.

        Returns
        -------
        id : hashable
            Unique id identifying the instrument this driver is connected to.

        """
        assert not args, 'Cannot use positional arguments for %s' % cls
        return frozenset(kwargs.items())

    def initialize(self):
        """Open a connection to an instrument.

        """
        message = fill(cleandoc(
            '''This method is used to open the connection with the
            instrument and should be implemented by classes
            subclassing BaseInstrument.'''),
            80)
        raise NotImplementedError(message)

    def finalize(self):
        """Close the connection to the instrument.

        """
        message = fill(cleandoc(
            '''This method is used to close the connection with the
            instrument and should be implemented by classes
            subclassing BaseInstrument.'''),
            80)
        raise NotImplementedError(message)

    def check_connection(self):
        """Check whether or not the cache is likely to have been corrupted.

        Returns
        -------
        status : bool
            True is the connection can be trusted, False otherwise.

        """
        return False

    @property
    def connected(self):
        """Return whether or not commands can be sent to the instrument.

        """
        message = fill(cleandoc(
            '''This method returns whether or not command can be
            sent to the instrument, and should be implemented by classes
            subclassing BaseInstrument.'''),
            80)
        raise NotImplementedError(message)

    def __enter__(self):
        """Context manager handling the connection to the instrument.

        """
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager handling the connection to the instrument.

        """
        self.finalize()


AbstractBaseDriver.register(BaseDriver)
