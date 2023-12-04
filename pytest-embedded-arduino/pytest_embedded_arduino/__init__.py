"""Make pytest-embedded plugin work with Arduino."""

from .app import ArduinoApp
from .serial import ArduinoSerial

__all__ = [
    'ArduinoApp',
    'ArduinoSerial',
]

__version__ = '1.4.2'
