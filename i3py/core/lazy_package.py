# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""A lazy module implementation based on a mapping of accessible classes.

"""
from types import ModuleType
from itertools import chain
from importlib import import_module


class LazyPackage(ModuleType):
    """A module which differs the import of objects.

    Typically, its main goal is to replace an __init__.py module hence allowing
    to differ the importing of the package module to their first access. All
    child lazy package can be safely imported.

    Parameters
    ----------
    lazy_imports : dict
        Dictionnary mapping the name accessible through lazy lodaing to their
        relative location as package.module.name

    name : str
        Name of the module. This should be set to __name__ when
        initializing the lazy module inside the module it should replace.

    doc : str
        Documentation of the module. This should be set to __doc__ when
        initializing the lazy module inside the module it should replace.

    local_vars : dict
        Local variable that should be accessible in this module. Typically this
        can be set to locals() when initializing the lazy module inside the
        module it should replace.

    Notes
    -----

    To use this inside an __init__.py file proceed as follow::

        import sys

        ... # define your lazy imports

        # At the end of the file
        sys.modules[__name__] = LazyPackage(lazy_imports, __name__, __doc__,
                                            locals()))

    """
    def __init__(self, lazy_imports, name, doc, local_vars):

        super().__init__(name, doc)
        self._lazy_imports = lazy_imports
        self._local_vars = local_vars
        lazy_modules = {}

        for key, val in local_vars.items():
            if isinstance(val, LazyPackage):
                lazy_modules[key] = val.__all__

        self.__all__ = list(chain(lazy_imports, local_vars,
                                  *[attrs for attrs in lazy_modules.values()]
                                  )
                            )
        self._lazy_modules = lazy_modules

    def __getattr__(self, attr_name):
        """When an attr is not found fall back to looking in the lazy imports.

        """
        if attr_name in self._lazy_imports:
            mod, attr = self._lazy_imports[attr_name].rsplit('.', 1)
            mod = mod if mod.startswith('.') else '.' + mod
            mod = import_module(mod, self.__package__)
            return getattr(mod, attr)

        if attr_name in self._local_vars:
            return self._local_vars[attr_name]

        for mod, attrs in self._lazy_modules.items():
            if attr_name in attrs:
                return getattr(self._local_vars[mod], attr_name)

        msg = f"module '{self.__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
