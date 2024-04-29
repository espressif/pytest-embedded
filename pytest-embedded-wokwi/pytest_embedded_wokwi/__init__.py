"""Make pytest-embedded plugin work with the Wokwi CLI."""

from .dut import WokwiDut
from .wokwi_cli import WokwiCLI

__all__ = [
    'WokwiCLI',
    'WokwiDut',
]

__version__ = '1.10.0'
