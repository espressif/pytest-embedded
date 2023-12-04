"""Make pytest-embedded plugin work with the Wokwi CLI."""

from .dut import WokwiDut  # noqa
from .wokwi_cli import WokwiCLI  # noqa

__all__ = [
    'WokwiCLI',
    'WokwiDut',
]

__version__ = '1.4.2'
