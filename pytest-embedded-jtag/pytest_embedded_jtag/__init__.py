"""Make pytest-embedded plugin work with JTAG."""

from ._telnetlib.telnetlib import Telnet
from .gdb import Gdb
from .openocd import OpenOcd

__all__ = [
    'Gdb',
    'OpenOcd',
    'Telnet',
]

__version__ = '1.13.0'
