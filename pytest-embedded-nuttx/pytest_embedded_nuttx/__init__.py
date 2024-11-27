"""Make pytest-embedded plugin work with NuttX."""

import importlib

from pytest_embedded.utils import lazy_load

from .dut import NuttxDut, NuttxEspDut, NuttxQemuDut, NuttxSerialDut

__getattr__ = lazy_load(
    importlib.import_module(__name__),
    {
        'NuttxDut': NuttxDut,
        'NuttxSerialDut': NuttxSerialDut,
        'NuttxEspDut': NuttxEspDut,  # requires 'esp' service
        'NuttxQemuDut': NuttxQemuDut,  # requires 'qemu' service
    },
    {
        'NuttxApp': '.app',  # requires 'esp' service
        'NuttxSerial': '.serial',  # requires 'esp' service
    },
)

__all__ = ['NuttxApp', 'NuttxSerial', 'NuttxSerialDut', 'NuttxQemuDut', 'NuttxEspDut', 'NuttxDut']

__version__ = '1.12.0'
