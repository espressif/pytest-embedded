"""Make pytest-embedded plugin work with the Wokwi CLI."""

WOKWI_CLI_MINIMUM_VERSION = '0.10.1'

from .dut import WokwiDut  # noqa
from .wokwi_cli import WokwiCLI  # noqa

__all__ = [
    'WOKWI_CLI_MINIMUM_VERSION',
    'WokwiCLI',
    'WokwiDut',
]

__version__ = '1.13.0'
