"""Make pytest-embedded plugin work with NuttX."""

import importlib

from pytest_embedded.utils import lazy_load

from .app import NuttxApp
from .dut import NuttxDut, NuttxSerialDut

__getattr__ = lazy_load(
    importlib.import_module(__name__),
    {
        'NuttxApp': NuttxApp,
        'NuttxDut': NuttxDut,
        'NuttxSerialDut': NuttxSerialDut,
    },
    {
        'NuttxSerial': '.serial',  # requires 'esp' service
        'NuttxEspDut': '.serial',  # requires 'esp' service
        'NuttxQemuDut': '.qemu',  # requires 'qemu' service
    },
)

__all__ = ['NuttxApp', 'NuttxDut', 'NuttxEspDut', 'NuttxQemuDut', 'NuttxSerial', 'NuttxSerialDut']

__version__ = '2.1.0'
