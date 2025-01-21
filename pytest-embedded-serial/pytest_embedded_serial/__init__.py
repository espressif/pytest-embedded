"""Make pytest-embedded plugin work with Serial."""

from .dut import SerialDut
from .serial import Serial

__all__ = [
    'Serial',
    'SerialDut',
]

__version__ = '1.13.0'
