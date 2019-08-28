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
from inspect import cleandoc
from textwrap import fill
from threading import RLock
from typing import Hashable
from weakref import WeakKeyDictionary, WeakValueDictionary

from .abstracts import AbstractBaseDriver
from .has_features import HasFeatures


class MissingVersionError(AttributeError):
    """Specific error notifying that a driver is missing a version string.

    """
    pass


class InstrumentSigleton(type):
    """Metaclass ensuring that a single driver is created per instrument.

    """

    _instances_cache: WeakKeyDictionary = WeakKeyDictionary()

    def __call__(cls, *args, **kwargs) -> 'BaseDriver':

        msg = ('%s does not have a version attr. All drivers must have a '
               'version string of the form "{major}.{minor}.{micro}" set '
               'in the __version__ attribute. It cannot be simply '
               'inherited.' % cls.__name__)

        # Enforce the presence of a version string per driver.
        if '__version__' not in dir(cls):
            raise MissingVersionError(msg)

        new_attr = set(dir(cls))
        for ancestor in cls.mro()[1:]:
            # New attributes not present on any parent class
            new_attr -= set(dir(ancestor))

        # Check that the version we have is not from a parent class
        if ('__version__' not in new_attr and
                any(cls.__version__ is getattr(ancestor, '__version__', '')
                    for ancestor in cls.mro()[1:])):
            raise MissingVersionError(msg)

        # This is done on first call rather than init to avoid useless memory
        # allocation.
        if cls not in cls._instances_cache:
            cls._instances_cache[cls] = WeakValueDictionary()

        cache = cls._instances_cache[cls]
        driver_id = cls.compute_id(args, kwargs)  # type: ignore
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

    """
    def __init__(self, *args, **kwargs):
        super(BaseDriver, self).__init__(kwargs.get('caching_allowed', True))

        self.owner = ''
        self.newly_created = True
        self.lock = RLock()

    @classmethod
    def compute_id(cls, args: tuple, kwargs: dict) -> Hashable:
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

    def check_connection(self) -> bool:
        """Check whether or not the cache is likely to have been corrupted.

        Returns
        -------
        status : bool
            True is the connection can be trusted, False otherwise.

        """
        return False

    def is_connected(self) -> bool:
        """Return whether or not commands can be sent to the instrument.

        """
        message = fill(cleandoc(
            '''This method returns whether or not command can be
            sent to the instrument, and should be implemented by classes
            subclassing BaseInstrument.'''),
            80)
        raise NotImplementedError(message)

    def __enter__(self) -> 'BaseDriver':
        """Context manager handling the connection to the instrument.

        """
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager handling the connection to the instrument.

        """
        self.finalize()


AbstractBaseDriver.register(BaseDriver)
