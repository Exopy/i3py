# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tools for instruments relying on the VISA protocol.

"""
import logging
import os
from inspect import cleandoc
from time import sleep
from typing import Any, Callable, ClassVar, Dict, List, Optional, Tuple, Union

from pyvisa import errors
from pyvisa.highlevel import ResourceManager
from pyvisa.rname import assemble_canonical_name, to_canonical_name

from ...core import subsystem
from ...core.actions import BaseAction
from ...core.base_driver import BaseDriver
from ...core.composition import SupportMethodCustomization
from ...core.errors import I3pyInterfaceNotSupported
from ...core.features import AbstractFeature

_RESOURCE_MANAGERS = None


def get_visa_resource_manager(backend='default'):
    """Access a VISA resource manager in use by I3py.

    """
    global _RESOURCE_MANAGERS
    if not _RESOURCE_MANAGERS:
        _RESOURCE_MANAGERS = {}

    if backend not in _RESOURCE_MANAGERS:

        if backend == 'default':
            def_backend = os.environ.get('I3PY_VISA', '@ni')
            mess = cleandoc('''Creating default Visa resource manager for I3py
                with backend {}.'''.format(def_backend))
            logging.debug(mess)
            _RESOURCE_MANAGERS[backend] = ResourceManager(def_backend)

        elif '@' in backend:
            _RESOURCE_MANAGERS[backend] = ResourceManager(backend)

    return _RESOURCE_MANAGERS[backend]


def set_visa_resource_manager(rm, backend='default'):
    """Set a VISA resource manager in use by I3py.

    This operation can only be performed once per backend id, and should be
    performed before any driver relying on this backend is created..

    Parameters
    ----------
    rm : ResourceManager
        Instance to use as Lantz resource manager.

    backend : str
        Id of the backend.

    """
    global _RESOURCE_MANAGERS
    assert isinstance(rm, ResourceManager)
    if _RESOURCE_MANAGERS and backend in _RESOURCE_MANAGERS:
        msg = 'Cannot set I3py VISA resource manager once one already exists.'
        raise ValueError(msg)

    if not _RESOURCE_MANAGERS:
        _RESOURCE_MANAGERS = {backend: rm}
    else:
        _RESOURCE_MANAGERS[backend] = rm


class VisaFeature(SupportMethodCustomization, property):
    """Special property used to wrap a property present in a Pyvisa resource.

    Visa properties are expected to be defined on the visa_resource subsystem.

    """

    def __init__(self, settable=True, deleter=None):
        super(VisaFeature, self).__init__(self._get,
                                          self._set if settable else None,
                                          deleter)
        self.name = None

    def clone(self):
        """Clone itself by inspecting the presence of setter/deleter.

        """
        return type(self)(self.fset is not None,
                          self.fdel)

    def create_default_settings(self):
        """A visa feature has no dynamic features.

        """
        return {}

    def make_doc(self, doc):
        """Do not alter the user doc.

        """
        return doc

    @property
    def self_alias(self) -> str:
        """For features self is replaced by feat in function signature.

        """
        return 'feat'

    def analyse_function(self, method_name: str, func: Callable,
                         specifiers: Tuple[str, ...]):
        """Check the signature of the function.

        """
        raise RuntimeError('VisaFeatures do not support customization.')

    def _get(self, obj):
        if obj.parent._resource:
            return getattr(obj.parent._resource, self.name)
        else:
            return obj.parent.resource_kwargs.get(self.name)

    def _set(self, obj, value):
        obj.parent.resource_kwargs[self.name] = value
        if obj.parent._resource:
            setattr(obj.parent._resource, self.name, value)


AbstractFeature.register(VisaFeature)


class VisaAction(BaseAction):
    """Action used for method modifying the VISA resource state.

    By default all calls to visa actions acquie the instrument lock to protect
    the instrument.

    """
    def __init__(self, **kwargs):
        kwargs.setdefault('lock', True)
        super().__init__(**kwargs)


def timeout_deleter(obj):
    del obj.parent.resource_kwargs['timeout']
    if obj.parent._resource:
        del obj.parent._resource.timeout


class BaseVisaDriver(BaseDriver):
    """Base class for instrument communicating through the VISA protocol.

    It handles the connection management, but not the subsequent communication.
    That's why driver should not inherit from it but from one of its derived
    class (save for very peculiar use).

    Parameters
    ----------
    resource_name : str, optional
        Name of the visa resource. can be specified as positional argument.

    backend : str, optional
        The PyVISA backend to use. This can either be a backend alias declared
        using set_visa_resource_manager or a valid string to create a pyvisa
        resource manager.

    parameters : dict, optional
        A dict to alter the driver attributes.

    caching_allowed : bool, optional
        Boolean use to determine if instrument properties can be cached

    kwargs :
        Arguments that PyVISA can use to build a resource name. Those depend
        on the interface type (*interface_type* keyword), please see PyVisa
        documentation for ore details.

    """
    #: Exceptions triggering a new communication attempts for Features with a
    #: non zero retries values.
    retries_exceptions = (TimeoutError, errors.VisaIOError,  # type: ignore
                          errors.InvalidSession)

    #: Interfaces supported by the instrument.
    #: For each type of interface a dictionary (or a list of dictionary),
    #: specifying the default arguments to use should be provided.
    #: For example::
    #:
    #:       {'USB': [{'resource_class': 'INSTR'},
    #:                {'resource_class': 'RAW'}],
    #:        'TCPIP': {'resource_class': 'SOCKET',
    #:                  'port': '50000'}
    INTERFACES: ClassVar[Dict[str, Union[Dict[str, str],
                                         List[Dict[str, str]]]]] = {}

    #: Default arguments passed to the Resource constructor on initialize.
    #: It should be specified in two layers, the first indicating the
    #: interface type and the second the corresponding arguments.
    #: The key COMMON is used to indicate keywords for all interfaces.
    #: For example:
    #:
    #:       {'ASRL':     {'read_termination': '\n',
    #:                     'baud_rate': 9600},
    #:        'USB':      {'read_termination': \r'},
    #:        'COMMON':   {'write_termination': '\n'}
    #:       }
    DEFAULTS: ClassVar[Optional[Dict[str, Dict[str, Any]]]] = None

    #: Tuple of keywords unrelated to Visa resource name. Used to remove them
    #: from the kwargs when building the resource name.
    NON_VISA_NAMES: ClassVar[Tuple[str, ...]] = ('parameters', 'backend')

    def __init__(self, *args, **kwargs):
        super(BaseVisaDriver, self).__init__(*args, **kwargs)

        # This entry is populated by the compute_id class method (called by the
        # the metaclass) from the provided information.
        r_name = kwargs['resource_name']

        rm = get_visa_resource_manager(kwargs.get('backend', 'default'))
        self._resource_manager = rm

        # Does not work with Visa alias
        r_info = self._resource_manager.resource_info(r_name)
        if r_info:
            #: Keyword arguments passed to the resource during initialization.
            kw = self._get_defaults_kwargs(r_info.interface_type.name.upper(),
                                           r_info.resource_class,
                                           kwargs.get('parameters', {}))
            self.resource_kwargs = kw
        else:
            # Allow to at least get the COMMON parameters.
            kw = self._get_defaults_kwargs(None,
                                           None,
                                           kwargs.get('parameters', {}))
            self.resource_kwargs = kw

        #: The resource name
        self.resource_name = r_name

        # The resource will be created when the driver is initialized.
        self._resource = None

    @classmethod
    def compute_id(cls, args, kwargs):
        """Assemble the resource name from the provided info.

        """
        rname = None
        if args:
            msg = 'A single positional argument is allowed for %s' % cls
            assert len(args) == 1, msg
            rname = args[0]
        elif 'resource_name' in kwargs:
            rname = kwargs['resource_name']

        if rname:
            try:
                kwargs['resource_name'] = to_canonical_name(rname)
            except Exception:  # TODO Use a more adequate exception
                # Fail silently to allow the use of VISA alias
                kwargs['resource_name'] = rname
        else:
            visa_infos = cls._get_visa_infos(kwargs)
            kwargs['resource_name'] =\
                assemble_canonical_name(**visa_infos)

        return kwargs['resource_name']

    @classmethod
    def _get_visa_infos(cls, connection_infos):
        """Filter out non-VISA related keywords and fill the gaps using
        INTERFACES

        """
        interface_type = connection_infos['interface_type']
        default_protocol = cls.INTERFACES.get(interface_type, {})
        if not isinstance(default_protocol, dict):
            default_protocol = default_protocol[0]

        visa_infos = {k: v for k, v in connection_infos.items()
                      if k not in cls.NON_VISA_NAMES}

        default_protocol.update(visa_infos)
        return default_protocol

    @classmethod
    def _get_defaults_kwargs(cls, interface_type, resource_class,
                             user_kwargs):
        """Compute the default keyword arguments.

        This is done by combining:
            - user provided keyword arguments.
            - (interface_type, resource_class) keyword arguments.
            - interface_type keyword arguments.
            - resource_class keyword arguments.
            - common keyword arguments.

        (the first ones have precedence)

        Parameters
        ----------
        interface_type : str|None, {'ASRL', 'USB', 'TCPIP', 'GPIB', 'PXI'}
            Type of interface.

        resource_class : str|None, {'INSTR', 'SOCKET', 'RAW'}
            Class of resource.

        Returns
        -------
        kwargs : dict
            The keyword arguments to use when opening a session.

        """
        if cls.DEFAULTS:

            kwargs = {}

            for key in ('COMMON', resource_class, interface_type,
                        (interface_type, resource_class)):
                if key not in cls.DEFAULTS:
                    continue
                value = cls.DEFAULTS[key]
                if value is None:
                    msg = 'An %s instrument is not supported by the driver %s'
                    raise I3pyInterfaceNotSupported(msg, key, cls.__name__)
                if value:
                    kwargs.update(value)

            if user_kwargs:
                kwargs.update(user_kwargs)

            return kwargs
        else:
            return user_kwargs

    def initialize(self):
        rm = self._resource_manager
        self._resource = rm.open_resource(self.resource_name,
                                          **self.resource_kwargs)

    def finalize(self):
        self._resource.close()
        self._resource = None

    def reopen_connection(self):
        """Close and re-open a suspicious connection.

        A VISA clear command is issued after re-opening the connection to make
        sure the instrument queues do not keep corrupted data. This might be
        an issue with some instruments in such a case simply override this
        method.

        """
        self.finalize()
        self.initialize()
        self._resource.clear()
        # Make sure the clear command completed before sending more commands.
        sleep(0.3)

    # --- Pyvisa wrappers

    #: Direct access to the visa resource.
    visa_resource = subsystem()

    with visa_resource as vr:

        #: The timeout in milliseconds for all resource I/O operations.
        #:
        #: None is mapped to VI_TMO_INFINITE.
        #: A value less than 1 is mapped to VI_TMO_IMMEDIATE.
        vr.timeout = VisaFeature(True, timeout_deleter)

        #: Pyvisa resource info.
        vr.resource_info = VisaFeature(settable=False)

        #: Pyvisa interface type
        vr.interface_type = VisaFeature(settable=False)

        @vr
        @VisaAction()
        def clear(self):
            """Clears this resource.

            """
            self.parent._resource.clear()

        @vr
        @VisaAction()
        def install_handler(self, event_type, handler, user_handle=None):
            """See Pyvisa docs.

            """
            return self.parent._resource.install_handler(event_type, handler,
                                                         user_handle)

        @vr
        @VisaAction()
        def uninstall_handler(self, event_type, handler, user_handle=None):
            """See Pyvisa docs.

            """
            self.parent._resource.uninstall_handler(event_type, handler,
                                                    user_handle)
