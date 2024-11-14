"""Make pytest-embedded plugin work with NuttX."""

import importlib

from pytest_embedded.utils import lazy_load

from .dut import NuttxDut, NuttxEspDut

__getattr__ = lazy_load(
    importlib.import_module(__name__),
    {
        'NuttxDut': NuttxDut,
        'NuttxEspDut': NuttxEspDut,  # requires 'esp' service
    },
    {
        'NuttxApp': '.app',  # requires 'esp' service
        'NuttxSerial': '.serial',  # requires 'esp' service
    },
)

__all__ = ['NuttxApp', 'NuttxSerial', 'NuttxEspDut', 'NuttxDut']

__version__ = '1.12.0'
