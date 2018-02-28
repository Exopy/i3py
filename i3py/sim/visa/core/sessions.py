# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Object representing a VISA session.

This file is largely inspired by the work done in PyVISA-Sim package.

"""
from pyvisa import constants, attributes, rname

from .common import logger


class Session(object):
    """A base class for Session objects.

    Just makes sure that common methods are defined and information is stored.

    Parameters
    ----------
    resource_manager_session:
        The session handle of the parent Resource Manager

    resource_name: str
        The resource name.

    parsed: str
        the parsed resource name (optional).

    """

    #: Maps (Interface Type, Resource Class) to Python class encapsulating that
    #: resource.
    #: dict[(Interface Type, Resource Class) , Session]
    _session_classes = dict()

    #: Session handler for the resource manager.
    session_type = None

    @classmethod
    def get_session_class(cls, interface_type, resource_class):
        """Return the session class for a given interface type and resource
        class.

        Parameters
        ----------
        interface_type: constants.InterfaceType
            The interface type to use for the session.

        resource_class: str
            The name of the resource class to use for the session.

        Returns
        -------
        session: Session
            Session class to use.

        """
        try:
            return cls._session_classes[(interface_type, resource_class)]
        except KeyError:
            raise ValueError('No class registered for %s, %s' %
                             (interface_type, resource_class))

    @classmethod
    def register(cls, interface_type, resource_class):
        """Register a session class for a given interface type and resource
        class.

        Parameters
        ----------
        interface_type: constants.InterfaceType
            The interface type for which to register the session class.

        resource_class: str
            The name of the resource class for which to register the session
            class.

        """
        def _internal(python_class):
            if (interface_type, resource_class) in cls._session_classes:
                logger.warning('%s is already registered in the '
                               'ResourceManager. Overwriting with %s' %
                               ((interface_type, resource_class), python_class)
                               )

            python_class.session_type = (interface_type, resource_class)
            cls._session_classes[(interface_type,
                                  resource_class)] = python_class
            return python_class
        return _internal

    def __init__(self, resource_manager_session, resource_name, parsed=None):
        if parsed is None:
            parsed = rname.parse_resource_name(resource_name)
        self.parsed = parsed
        self.attrs = {constants.VI_ATTR_RM_SESSION: resource_manager_session,
                      constants.VI_ATTR_RSRC_NAME: str(parsed),
                      constants.VI_ATTR_RSRC_CLASS: parsed.resource_class,
                      constants.VI_ATTR_INTF_TYPE: parsed.interface_type_const}
        self.after_parsing()

        #: devices.Device
        self.device = None

    def after_parsing(self):
        """Override in derived class to be executed after the resource name has
        been parsed and the attr dictionary has been filled.
        """
        pass

    def get_attribute(self, attribute):
        """Get an attribute from the session.

        :param attribute:
        :return: attribute value, status code
        :rtype: object, constants.StatusCode
        """

        # Check that the attribute exists.
        try:
            attr = attributes.AttributesByID[attribute]
        except KeyError:
            return 0, constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is valid for this session type.
        if not attr.in_resource(self.session_type):
            return 0, constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is readable.
        if not attr.read:
            raise Exception('Do not now how to handle write only attributes.')

        # Return the current value of the default according the VISA spec
        return (self.attrs.setdefault(attribute, attr.default),
                constants.StatusCode.success)

    def set_attribute(self, attribute, attribute_state):
        """Get an attribute from the session.

        :param attribute:
        :return: attribute value, status code
        :rtype: object, constants.StatusCode
        """

        # Check that the attribute exists.
        try:
            attr = attributes.AttributesByID[attribute]
        except KeyError:
            return constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is valid for this session type.
        if not attr.in_resource(self.session_type):
            return constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is writable.
        if not attr.write:
            return constants.StatusCode.error_attribute_read_only

        try:
            self.attrs[attribute] = attribute_state
        except ValueError:
            return constants.StatusCode.error_nonsupported_attribute_state

        return constants.StatusCode.success
