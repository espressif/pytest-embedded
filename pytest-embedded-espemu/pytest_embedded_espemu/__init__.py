"""Make pytest-embedded plugin work with esp-emu."""

import importlib

from pytest_embedded.utils import lazy_load

DEFAULT_IMAGE_FN = 'espemu_image.bin'

from .dut import EspEmuDut  # noqa
from .espemu import EspEmu  # noqa

__getattr__ = lazy_load(
    importlib.import_module(__name__),
    {
        'EspEmu': EspEmu,
        'EspEmuDut': EspEmuDut,
    },
    {
        'EspEmuApp': '.app',  # requires idf
    },
)


__all__ = [
    'DEFAULT_IMAGE_FN',
    'EspEmu',
    'EspEmuApp',
    'EspEmuDut',
]

__version__ = '2.8.1'
