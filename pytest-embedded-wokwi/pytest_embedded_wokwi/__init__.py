"""Make pytest-embedded plugin work with the Wokwi CLI."""

WOKWI_CLI_MINIMUM_VERSION = '0.10.1'

from .dut import WokwiDut  # noqa
from .wokwi import Wokwi  # noqa

__all__ = [
    'WOKWI_CLI_MINIMUM_VERSION',
    'Wokwi',
    'WokwiDut',
]

__version__ = '2.1.0'
