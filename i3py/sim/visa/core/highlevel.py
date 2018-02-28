# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Simulated implementation of a Visa library

"""
import random

from pyvisa import constants, highlevel, rname
import pyvisa.errors as errors
from pyvisa.compat import OrderedDict

from . import sessions, devices

# This import is required to register subclasses
from .resources import gpib, serial, tcpip, usb


class I3pySimVisaLibrary(highlevel.VisaLibraryBase):
    """Simulated VISA library.

    Notes
    -----
    Only supports messages based instrument at the time and only sync methods.

    """

    @staticmethod
    def get_debug_info():
        """Return a list of lines with backend info.
        """
        from .version import __version__
        d = OrderedDict()
        d['Version'] = '%s' % __version__

        return d

    def _init(self):

        #: map session handle to session object.
        #: dict[int, SessionSim]
        self.sessions = {}

        self.devices = devices.Devices()

    def _register(self, obj):
        """Creates a random but unique session handle for a session object,
        register it in the sessions dictionary and return the value

        Parameters
        ----------
        obj : Session
            A session object

        Returns
        -------
        session_handle : int

        """
        session = None

        while session is None or session in self.sessions:
            session = random.randint(1000000, 9999999)

        self.sessions[session] = obj
        return session

    def open(self, session, resource_name,
             access_mode=constants.AccessModes.no_lock,
             open_timeout=constants.VI_TMO_IMMEDIATE):
        """Opens a session to the specified resource.

        Corresponds to viOpen function of the VISA library.

        Parameters
        ----------
        session : int
            Resource Manager session (should always be a session returned
            from open_default_resource_manager()).

        resource_name : unicode
            Unique symbolic name of a resource.

        access_mode : constants.AccessModes
            Specifies the mode by which the resource is to be accessed.

        open_timeout: float
            Specifies the maximum time period (in milliseconds) that this
            operation waits before returning an error.

        Returns
        -------
        session : int
            Unique logical identifier reference to a session

        ret_code : pyvisa.constants.StatusCode`
            Return value of the library call.

        """
        try:
            open_timeout = int(open_timeout)
        except ValueError:
            raise ValueError('open_timeout (%r) must be an integer (or '
                             'compatible type)' % open_timeout)

        try:
            parsed = rname.parse_resource_name(resource_name)
        except rname.InvalidResourceName:
            return 0, constants.StatusCode.error_invalid_resource_name

        # Loops through all session types, tries to parse the resource name and
        # if ok, open it.
        cls = sessions.Session.get_session_class(parsed.interface_type_const,
                                                 parsed.resource_class)

        sess = cls(session, resource_name, parsed)

        try:
            sess.device = self.devices[sess.attrs[constants.VI_ATTR_RSRC_NAME]]
        except KeyError:
            return 0, constants.StatusCode.error_resource_not_found

        return self._register(sess), constants.StatusCode.success

    def close(self, session):
        """Closes the specified session, event, or find list.

        Corresponds to viClose function of the VISA library.

        Parameters
        ----------
        session : int
            Unique logical identifier to a session, event, or find list

        Returns
        -------
        res : pyvisa.constants.StatusCode
            Return value of the library call.

        """
        try:
            del self.sessions[session]
            return constants.StatusCode.success
        except KeyError:
            return constants.StatusCode.error_invalid_object

    def open_default_resource_manager(self):
        """This function returns a session to the Default Resource Manager
        resource.

        Corresponds to viOpenDefaultRM function of the VISA library.

        Returns
        -------
        session : int
            Unique logical identifier to a Default Resource Manager session

        ret_code : pyvisa.constants.StatusCode
            Return value of the library call

        """
        return self._register(self), constants.StatusCode.success

    def list_resources(self, session, query='?*::INSTR'):
        """Returns a tuple of all connected devices matching query.

        """
        # For each session type, ask for the list of connected resources and
        # merge them into a single list.
        resources = self.devices.list_resources()

        resources = rname.filter(resources, query)

        if resources:
            return resources

        err_code = errors.StatusCode.error_resource_not_found.value
        raise errors.VisaIOError(err_code)

    def read(self, session, count):
        """Reads data from device or interface synchronously.

        Corresponds to viRead function of the VISA library.

        Parameters
        ----------
        session : int
            Unique logical identifier to a session.

        count : int
            Number of bytes to be read.

        Returns
        -------
        data : bytes
            Data read

        ret_code : pyvisa.constants.StatusCode
            Return value of the library call.

        """
        try:
            sess = self.sessions[session]
        except KeyError:
            return b'', constants.StatusCode.error_invalid_object

        try:
            chunk, status = sess.read(count)
            if status == constants.StatusCode.error_timeout:
                raise errors.VisaIOError(constants.VI_ERROR_TMO)
            return chunk, status
        except AttributeError:
            return b'', constants.StatusCode.error_nonsupported_operation

    def write(self, session, data):
        """Writes data to device or interface synchronously.

        Corresponds to viWrite function of the VISA library.

        Parameters
        ----------
        session : int
            Unique logical identifier to a session.

        data : str
            Data to be written

        Returns
        -------
        written : int
            Number of bytes actually transferred

        ret_code : pyvisa.constants.StatusCode
            Return value of the library call.

        """

        try:
            sess = self.sessions[session]
        except KeyError:
            return constants.StatusCode.error_invalid_object

        try:
            return sess.write(data)
        except AttributeError:
            return constants.StatusCode.error_nonsupported_operation

    def get_attribute(self, session, attribute):
        """Retrieves the state of an attribute.

        Corresponds to viGetAttribute function of the VISA library.

        Parameters
        ----------
        session : int
            Unique logical identifier to a session, event or find list.

        attribute :
            Resource attribute for which the state query is made
            (see Attributes.*)

        Returns
        -------
        state : unicode
            The state of the queried attribute for a specified resource

        ret_code : pyvisa.constants.StatusCode
            Return value of the library call.

        """
        try:
            sess = self.sessions[session]
        except KeyError:
            return 0, constants.StatusCode.error_invalid_object

        return sess.get_attribute(attribute)

    def set_attribute(self, session, attribute, attribute_state):
        """Sets the state of an attribute.

        Corresponds to viSetAttribute function of the VISA library.

        Parameters
        ----------
        session : int
            Unique logical identifier to a session.

        attribute : unicode
            Attribute for which the state is to be modified. (Attributes.*)

        attribute_state :
            The state of the attribute to be set for the specified object.

        Returns
        -------
        ret_code : pyvisa.constants.StatusCode
            Return value of the library call.

        """
        try:
            sess = self.sessions[session]
        except KeyError:
            return constants.StatusCode.error_invalid_object

        return sess.set_attribute(attribute, attribute_state)

    def disable_event(self, session, event_type, mechanism):
        # TODO: implement this for GPIB finalization
        pass

    def discard_events(self, session, event_type, mechanism):
        # TODO: implement this for GPIB finalization
        pass

    # TODO add missing methods
