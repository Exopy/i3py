# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test for the VISA backend.

"""
import os

import pytest

pytest.importorskip('pyvisa')
pytest.importorskip('pyvisa-sim')

from pyvisa.highlevel import ResourceManager
from pyvisa.rname import to_canonical_name
from i3py.core.features import Float
from i3py.core.errors import I3pyInterfaceNotSupported
from i3py.backends.visa import (get_visa_resource_manager,
                                set_visa_resource_manager,
                                BaseVisaDriver,
                                VisaMessageDriver,
                                VisaRegistryDriver,
                                errors,
                                )

base_backend = os.path.join(os.path.dirname(__file__), 'base.yaml@sim')


# --- Test resource managers handling -----------------------------------------

@pytest.yield_fixture
def cleanup():
    os.environ['I3PY_VISA'] = '@py'
    yield
    import i3py.backends.visa.base as lv
    lv._RESOURCE_MANAGERS = None
    del os.environ['I3PY_VISA']


def test_get_visa_resource_manager(cleanup):

    rm = get_visa_resource_manager()
    assert rm is get_visa_resource_manager('@py')
    # Make sure we do not override existing RMs
    os.environ['I3PY_VISA'] = '@sim'
    assert rm is get_visa_resource_manager()

    assert rm is not get_visa_resource_manager('@sim')
    import i3py.backends.visa.base as lv
    assert len(lv._RESOURCE_MANAGERS) == 3


def test_set_visa_resource_manager(cleanup):

    rm = ResourceManager('@py')
    set_visa_resource_manager(rm, '@py')
    assert rm is get_visa_resource_manager('@py')

    with pytest.raises(ValueError):
        set_visa_resource_manager(rm, '@py')

    rm = ResourceManager('@sim')
    set_visa_resource_manager(rm, '@sim')
    assert rm is get_visa_resource_manager('@sim')


# --- Test base driver capabilities -------------------------------------------

@pytest.fixture
def visa_driver():
    """Fixture returning a basic visa driver.

    """
    BaseVisaDriver.__version__ = '0.1.0'
    return BaseVisaDriver(**{'interface_type': 'TCPIP',
                             'host_address': '192.168.0.100',
                             'backend': base_backend})


class TestBaseVisaDriver(object):

    def test_visa_driver_unicity(self, visa_driver):
        """Test that visa name normalization ensure driver unicity.

        """
        rname = 'TCPIP::192.168.0.100::INSTR'
        driver2 = BaseVisaDriver(**{'resource_name': rname,
                                    'backend': base_backend})
        assert visa_driver.resource_name == driver2.resource_name
        assert visa_driver is driver2

    def test_handling_a_visa_alias(self):
        """Check that a visa alias can be accepted.

        """
        rname = 'visa_alias'
        driver = BaseVisaDriver(rname, backend=base_backend)
        assert driver.resource_name == 'visa_alias'

    def test_filling_infos_from_INTERFACES(self):
        """Test that info provided in the INTERFACES class attribute are
        correctly picked

        """
        class TestVisaDriver(BaseVisaDriver):

            __version__ = '0.1.0'

            INTERFACES = {'TCPIP': {'resource_class': 'SOCKET',
                                    'port': 5025}}

        driver = TestVisaDriver(**{'interface_type': 'TCPIP',
                                   'host_address': '192.168.0.100',
                                   'backend': base_backend})

        rname = 'TCPIP::192.168.0.100::5025::SOCKET'
        driver2 = TestVisaDriver(**{'resource_name': rname,
                                    'backend': base_backend})

        assert driver.resource_name == driver2.resource_name
        assert driver is driver2

        TestVisaDriver.INTERFACES = {'TCPIP': [{'resource_class': 'INSTR',
                                                'lan_device_name': 'inst1'},
                                               {'resource_class': 'SOCKET',
                                                'port': 5025}]}

        driver = TestVisaDriver(**{'interface_type': 'TCPIP',
                                   'host_address': '192.168.0.100',
                                   'backend': base_backend})

        rname = 'TCPIP::192.168.0.100::inst1::INSTR'
        driver2 = TestVisaDriver(**{'resource_name': rname,
                                    'backend': base_backend})

        assert driver.resource_name == driver2.resource_name
        assert driver is driver2

    def test_using_default_and_para(self):
        """Test mixing default parameters and user custom ones.

        """
        class TestDefaultVisa(VisaMessageDriver):

            __version__ = '0.1.0'

            DEFAULTS = {'TCPIP': {'read_termination': '\n'},
                        'COMMON': {'write_termination': '\n',
                                   'timeout': 10}}

        driver = TestDefaultVisa(**{'interface_type': 'TCPIP',
                                    'host_address': '192.168.0.1',
                                    'backend': base_backend,
                                    'parameters': {'timeout': 5}})

        assert driver.resource_kwargs == {'read_termination': '\n',
                                          'write_termination': '\n',
                                          'timeout': 5}

    def test_using_forbidden_interface(self):
        """Test creating an instance for a forbidden interface type.

        """
        class TestDefaultVisa(VisaMessageDriver):

            __version__ = '0.1.0'

            DEFAULTS = {'TCPIP': None,
                        'COMMON': {'write_termination': '\n',
                                   'timeout': 10}}

        with pytest.raises(I3pyInterfaceNotSupported):
            TestDefaultVisa(**{'interface_type': 'TCPIP',
                               'host_address': '192.168.0.1',
                               'backend': base_backend,
                               'parameters': {'timeout': 5}})

    def test_filtering_kwargs(self):
        """Test filtering keyword arguments.

        """
        class SpecialKwargsVisa(BaseVisaDriver):

            __version__ = '0.1.0'

            NON_VISA_NAMES = ('parameters', 'backend', 'my_own')

        rname = 'visa_alias'
        driver = BaseVisaDriver(rname, backend=base_backend, my_own=1)
        assert driver.resource_name == 'visa_alias'

    @pytest.mark.xfail
    def test_clear(self, visa_driver):
        """Test clearing an instrument.

        """
        visa_driver.initialize()
        with pytest.raises(NotImplementedError):
            visa_driver.visa_resource.clear()

    def test_resource_info(self, visa_driver):
        """Test querying the underlying resource info.

        """
        visa_driver.initialize()
        assert visa_driver.visa_resource.resource_info

    def test_interface_type(self, visa_driver):
        """Test querying the underlying resource interface type.

        """
        visa_driver.initialize()
        assert visa_driver.visa_resource.interface_type

    def test_timeout(self, visa_driver):
        """Test the timeout descriptor.

        """
        visa_driver.visa_resource.timeout = 10
        visa_driver.initialize()
        assert visa_driver.visa_resource.timeout == 10
        del visa_driver.visa_resource.timeout
        assert visa_driver.visa_resource.timeout == float('+inf')

    def test_reopen_connection(self, visa_driver, monkeypatch):
        """Test reopening a connections.

        """
        class Witness(object):

            def __init__(self):
                self.called = 0

            def __call__(self):
                self.called += 1

        visa_driver.initialize()
        visa_driver.visa_resource.timeout = 20
        w = Witness()
        monkeypatch.setattr(type(visa_driver._resource), 'clear',  w)

        visa_driver.reopen_connection()
        assert visa_driver._resource
        assert w.called == 1
        assert visa_driver.visa_resource.timeout == 20

    @pytest.mark.xfail
    def test_install_handler(self, visa_driver):
        """Test clearing an instrument.

        """
        visa_driver.initialize()
        with pytest.raises(NotImplementedError):
            visa_driver.visa_resource.install_handler(None, None)

    @pytest.mark.xfail
    def test_uninstall_handler(self, visa_driver):
        """Test clearing an instrument.

        """
        visa_driver.initialize()
        with pytest.raises(errors.UnknownHandler):
            visa_driver.visa_resource.uninstall_handler(None, None)


# --- Test message driver specific methods ------------------------------------

class VisaMessage(VisaMessageDriver):

    __version__ = '0.1.0'

    INTERFACES = {'USB': {'resource_class': 'INSTR',
                          'manufacturer_id': '0xB21',
                          'model_code': '0x39'}}


class VisaMessage2(VisaMessageDriver):

    __version__ = '0.1.0'

    INTERFACES = {'USB': {'resource_class': 'RAW',
                          'manufacturer_id': '0xB21',
                          'model_code': '0x39'}}


class TestVisaMessageDriver(object):

    def test_via_usb_instr(self):

        driver = VisaMessage.via_usb('90N326143',
                                     backend=base_backend)
        assert driver.resource_name ==\
            to_canonical_name('USB::0xB21::0x39::90N326143::INSTR')
        driver.initialize()

    def test_via_usb_instr_no_serial(self):

        driver = VisaMessage.via_usb(backend=base_backend)
        assert driver.resource_name ==\
            to_canonical_name('USB::0xB21::0x39::90N326143::INSTR')
        driver.initialize()

    def test_via_usb_instr_multiple_models(self):

        with pytest.raises(ValueError):
            VisaMessage.via_usb(model_code=('0x39', '0x40'),
                                backend=base_backend)

        with pytest.raises(ValueError):
            VisaMessage.via_usb(model_code=('0x50',),
                                backend=base_backend)

        driver = VisaMessage.via_usb('90N326143',
                                     model_code=('0x39', '0x40'),
                                     backend=base_backend)
        assert driver.resource_name ==\
            to_canonical_name('USB::0xB21::0x39::90N326143::INSTR')
        driver.initialize()

    def test_via_usb_raw(self):

        driver = VisaMessage2.via_usb_raw('90N326145',
                                          backend=base_backend)
        assert driver.resource_name ==\
            to_canonical_name('USB::0xB21::0x39::90N326145::RAW')
        driver.initialize()

    def test_via_usb_raw_no_instr(self):

        with pytest.raises(ValueError):
            VisaMessage2.via_usb_raw('90N326146', backend=base_backend)

    def test_via_tcpip_instr(self):

        driver = VisaMessage.via_tcpip('192.168.0.100',
                                       backend=base_backend)
        assert driver.resource_name ==\
            to_canonical_name('TCPIP::192.168.0.100::inst0::INSTR')
        driver.initialize()

    def test_via_tcpip_socket(self):

        driver = VisaMessage.via_tcpip_socket('192.168.0.100', 5025,
                                              backend=base_backend)
        assert driver.resource_name ==\
            to_canonical_name('TCPIP::192.168.0.100::5025::SOCKET')
        driver.initialize()

    def test_via_serial(self):

        driver = VisaMessage.via_serial(1, backend=base_backend)
        assert driver.resource_name == to_canonical_name('ASRL1::INSTR')
        driver.initialize()

    def test_via_gpib(self):

        driver = VisaMessage.via_gpib(1, backend=base_backend)
        assert driver.resource_name == to_canonical_name('GPIB::1::INSTR')
        driver.initialize()

    def test_feature(self):
        """Test getting and setting a feature.

        """
        class TestFeature(VisaMessageDriver):

            __version__ = '0.1.0'

            freq = Float('?FREQ', 'FREQ {}')

            DEFAULTS = {'COMMON': {'write_termination': '\n',
                                   'read_termination': '\n'}}

            def default_check_operation(self, feat, value, i_value,
                                        state=None):
                return True, ''

        d = TestFeature.via_tcpip('192.168.0.100', backend=base_backend)
        d.initialize()
        assert d.freq == 100.0
        d.freq = 10.
        assert d.freq == 10.

    def test_status_byte(self):
        pass

#    def test_write_raw(self):
#
#        with pytest.raises(NotImplementedError):
#            self.driver.write_raw('')
#
#    def test_write(self):
#        with pytest.raises(NotImplementedError):
#            self.driver.write('')
#
#    def test_write_ascii_values(self):
#
#        with pytest.raises(NotImplementedError):
#            self.driver.write_ascii_values('VAL', range(10), 'f', ',')

    def test_write_binary_values(self):

        pass

    def test_read_raw(self, size=None):

        pass

    def test_read(self):

        pass

    def test_read_values(self):

        pass

    def test_query(self):

        pass

    def test_query_ascii_values(self):

        pass

    def test_query_binary_values(self):

        pass


class TestVisaRegistryDriver(object):
    """Test the VisaRegistryDriver capabilities.

    Use an abstract visa library as we don't have a simulated backend yet.

    """
    def test_move_in(self):

        pass

    def test_move_out(self):

        pass

    def test_read_memory(self):

        pass

    def test_write_memory(self):

        pass
