"""Make pytest-embedded plugin work with QEMU."""

DEFAULT_IMAGE_FN = 'flash_image.bin'
ENCRYPTED_IMAGE_FN = f'encrypted_{DEFAULT_IMAGE_FN}'

from .app import QemuApp  # noqa
from .dut import QemuDut  # noqa
from .qemu import Qemu  # noqa

__all__ = [
    'DEFAULT_IMAGE_FN',
    'ENCRYPTED_IMAGE_FN',
    'Qemu',
    'QemuApp',
    'QemuDut',
]

__version__ = '1.4.2'
