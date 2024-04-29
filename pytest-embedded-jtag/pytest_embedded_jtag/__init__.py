"""Make pytest-embedded plugin work with JTAG."""

from .gdb import Gdb
from .openocd import OpenOcd

__all__ = [
    'Gdb',
    'OpenOcd',
]

__version__ = '1.10.0'
