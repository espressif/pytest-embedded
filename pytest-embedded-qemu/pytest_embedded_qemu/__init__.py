"""Make pytest-embedded plugin work with QEMU."""

import importlib

from pytest_embedded.utils import lazy_load

DEFAULT_IMAGE_FN = 'flash_image.bin'
ENCRYPTED_IMAGE_FN = f'encrypted_{DEFAULT_IMAGE_FN}'

from .dut import QemuDut  # noqa
from .qemu import Qemu  # noqa


__getattr__ = lazy_load(
    importlib.import_module(__name__),
    {
        'Qemu': Qemu,
        'QemuDut': QemuDut,
    },
    {
        'QemuApp': '.app',  # requires idf
    },
)


__all__ = [
    'DEFAULT_IMAGE_FN',
    'ENCRYPTED_IMAGE_FN',
    'Qemu',
    'QemuApp',
    'QemuDut',
]

__version__ = '2.1.0'
