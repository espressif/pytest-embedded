"""Make pytest-embedded plugin work with Arduino."""

import importlib

from pytest_embedded.utils import lazy_load

from .app import ArduinoApp

__getattr__ = lazy_load(
    importlib.import_module(__name__),
    {
        'ArduinoApp': ArduinoApp,
    },
    {
        'ArduinoSerial': '.serial',  # requires esp
    },
)

__all__ = ['ArduinoApp', 'ArduinoSerial']


__version__ = '2.1.0'
