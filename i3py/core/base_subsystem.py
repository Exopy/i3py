# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Subsystems can be used to give a hierarchical organisation to a driver.

"""
from .abstracts import AbstractSubSystem, AbstractSubSystemDescriptor
from .has_features import HasFeatures
from .utils import check_options


class SubSystem(HasFeatures):
    """SubSystem allow to split the implementation of a driver into multiple
    parts.

    This mechanism allow to avoid crowding the instrument namespace with very
    long Feature names.

    Attributes
    ----------
    parent : HasFeatures
        Parent object of the subsystem.

    """
    def __init__(self, parent, **kwargs):
        super(SubSystem, self).__init__(**kwargs)
        self.parent = parent

    @property
    def lock(self):
        """Access to parent lock."""
        return self.parent.lock

    def reopen_connection(self):
        """Subsystems simply pipes the call to their parent.

        """
        self.parent.reopen_connection()

    def default_get_feature(self, feat, cmd, *args, **kwargs):
        """Subsystems simply pipes the call to their parent.

        """
        return self.parent.default_get_feature(feat, cmd, *args, **kwargs)

    def default_set_feature(self, feat, cmd, *args, **kwargs):
        """Subsystems simply pipes the call to their parent.

        """
        return self.parent.default_set_feature(feat, cmd, *args, **kwargs)

    def default_check_operation(self, feat, value, i_value, response):
        """Subsystems simply pipes the call to their parent.

        """
        return self.parent.default_check_operation(feat, value, i_value,
                                                   response)

AbstractSubSystem.register(SubSystem)


class SubSystemDescriptor(object):
    """Descriptor giving access to a subsytem.

    The subsystem is returned only if the proper conditions are matched
    in terms of static options (as specified through the options of the
    subsystem declarator).

    """
    __slots__ = ('cls', 'name', 'options')

    def __init__(self, cls, name, options):
        self.cls = cls
        self.name = name
        self.options = options

    def __get__(self, instance, cls):
        if instance is None:
            return self.cls
        else:
            if self.name not in instance._subsystem_instances:
                if self.options:
                    test, msg = check_options(instance, self.options)
                    if not test:
                        ex_msg = ('%s is not accessible with instrument '
                                  'options: %s')
                        raise AttributeError(ex_msg % (self.name, msg))

                ss = self.cls(parent=instance)
                instance._subsystem_instances[self.name] = ss

            return instance._subsystem_instances[self.name]


AbstractSubSystemDescriptor.register(SubSystemDescriptor)
