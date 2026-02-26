"""Make pytest-embedded plugin work with the Wokwi CLI."""

from .dut import WokwiDut
from .wokwi import Wokwi

__all__ = [
    'Wokwi',
    'WokwiDut',
]

__version__ = '2.6.0'
