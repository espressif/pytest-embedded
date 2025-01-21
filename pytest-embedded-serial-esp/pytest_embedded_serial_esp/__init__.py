"""Make pytest-embedded plugin work with Espressif target boards."""

from .serial import EspSerial

__all__ = [
    'EspSerial',
]

__version__ = '1.13.0'
