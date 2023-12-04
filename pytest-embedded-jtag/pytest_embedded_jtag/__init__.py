"""Make pytest-embedded plugin work with JTAG."""

from .gdb import Gdb
from .openocd import OpenOcd

__all__ = [
    'OpenOcd',
    'Gdb',
]

__version__ = '1.4.2'
