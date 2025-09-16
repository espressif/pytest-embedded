import contextlib
import logging
import os
import re
import subprocess
import typing as t

from packaging.version import Version
from pytest_embedded.log import MessageQueue, live_print_call
from pytest_embedded_idf.app import IdfApp

from . import DEFAULT_IMAGE_FN, ENCRYPTED_IMAGE_FN


class IdfFlashImageMaker:
    """
    Create a single image for QEMU based on the `IdfApp`'s partition table and all the flash files.
    """

    XTENSA_FLASH_BIN_SIZES: t.ClassVar[list[tuple[int, str]]] = [
        (2 * 1024 * 1024, '2MB'),
        (4 * 1024 * 1024, '4MB'),
        (8 * 1024 * 1024, '8MB'),
        (16 * 1024 * 1024, '16MB'),
    ]

    RISCV_FLASH_BIN_SIZES: t.ClassVar[list[tuple[int, str]]] = [
        (2 * 1024 * 1024, '2MB'),
        (4 * 1024 * 1024, '4MB'),
        (8 * 1024 * 1024, '8MB'),
        (16 * 1024 * 1024, '16MB'),
    ]

    def __init__(self, app: 'QemuApp', image_path: str, *, qemu_version: Version = Version('8.0.0')):
        """
        Args:
            app: `IdfApp` instance
            image_path: output image path
        """
        self.app = app
        self.image_path = image_path
        self.qemu_version = qemu_version

    def _get_upper_bound(self, size: int, ranges: list[tuple[int, str]]) -> str:
        for r, s in ranges:
            if size <= r:
                upper = s
                break
        else:
            raise ValueError(f'Flash size {size} is too big for QEMU, max is {ranges[-1][1]}')

        return upper

    @property
    def qemu_flash_size(self) -> str:
        """
        Get QEMU flash size.

        If `flash_size` is set to `keep` or `detect`, the size will be automatically detected.
        Otherwise, the size will be taken from `flash_size` settings.

        Returns:
            QEMU flash size

        Warning:
            QEMU < 8.0.0 only support 4MB flash image size for xtensa.
        """
        if self.app.is_xtensa and self.qemu_version < Version('8.0.0'):
            return '4MB'  # QEMU < 8.0.0 only support 4MB flash image size

        if self.app.flash_settings.get('flash_size') not in ['keep', 'detect']:
            # 2MB-c1, 4MB-ci
            return self.app.flash_settings['flash_size'].split('-')[0]

        # detect flash size
        qemu_flash_size = self.app.flash_files[-1].offset + os.stat(self.app.flash_files[-1].file_path).st_size
        if self.app.is_xtensa:
            return self._get_upper_bound(qemu_flash_size, self.XTENSA_FLASH_BIN_SIZES)
        else:
            return self._get_upper_bound(qemu_flash_size, self.RISCV_FLASH_BIN_SIZES)

    def make_bin(self) -> None:
        """
        Create a single image file for qemu.
        """
        live_print_call(
            [
                'esptool.py',
                '--chip',
                self.app.target,
                'merge-bin',
                '-o',
                self.image_path,
                '--fill-flash-size',
                self.qemu_flash_size,
                *self.app.write_flash_args,
            ],
            cwd=self.app.binary_path,
        )

        if self.app.encrypt:
            if self.app.keyfile is None or not os.path.exists(self.app.keyfile):
                raise ValueError("Flash Encryption key file doesn't exist")
            self._write_encrypted_bin()

    def _write_encrypted_bin(self, seek: int = 0):
        live_print_call(
            [
                'espsecure.py',
                'encrypt_flash_data',
                '--keyfile',
                self.app.keyfile,
                '--output',
                self.app.encrypted_image_path,
                '--address',
                str(seek),
                self.image_path,
            ],
        )

    def _burn_efuse(self):
        pass


class QemuApp(IdfApp):
    """
    QEMU App class

    Attributes:
        image_path (str): QEMU flash-able bin path
    """

    QEMU_VERSION_REGEX = re.compile(r'QEMU emulator version (\d+\.\d+\.\d+)')
    QEMU_PROG_FMT = 'qemu-system-{}'

    # the qemu version shouldn't change in the same session
    _QEMU_VERSION = None

    def __init__(
        self,
        msg_queue: MessageQueue,
        qemu_image_path: str | None = None,
        skip_regenerate_image: bool | None = False,
        encrypt: bool | None = False,
        keyfile: str | None = None,
        qemu_prog_path: str | None = None,
        **kwargs,
    ):
        self._q = msg_queue

        super().__init__(**kwargs)

        self.qemu_prog_path = qemu_prog_path or self.QEMU_PROG_FMT.format('xtensa' if self.is_xtensa else 'riscv32')
        self.image_path = qemu_image_path or os.path.join(self.binary_path, DEFAULT_IMAGE_FN)
        self.skip_regenerate_image = skip_regenerate_image
        self.encrypt = encrypt
        self.keyfile = keyfile

        if self.encrypt:
            self.encrypted_image_path = os.path.join(self.binary_path, ENCRYPTED_IMAGE_FN)

        self.create_image()

    @property
    def qemu_version(self) -> Version:
        """
        Get QEMU version

        Returns:
            QEMU version
        """

        if self._QEMU_VERSION is not None:
            return self._QEMU_VERSION

        s = subprocess.check_output([self.qemu_prog_path, '--version'], encoding='utf-8')
        version = self.QEMU_VERSION_REGEX.search(s)
        if version is None:
            raise ValueError(f'Could not parse QEMU version from {s}')

        self._QEMU_VERSION = Version(version.group(1))
        logging.debug('QEMU version: %s', self._QEMU_VERSION)
        return self._QEMU_VERSION

    def create_image(self) -> None:
        """
        Create the image, if it doesn't exist.
        """
        if os.path.exists(self.image_path) and self.skip_regenerate_image:
            logging.info(f'Using existing image: {self.image_path}')
        else:
            try:
                import esptool  # noqa
            except ImportError:
                raise ImportError(
                    'esptool is required for creating QEMU images. '
                    'Please install esptool with "pip install -U esptool" or use an existing image.'
                )

            with contextlib.redirect_stdout(self._q):
                image_maker = IdfFlashImageMaker(self, self.image_path, qemu_version=self.qemu_version)
                image_maker.make_bin()
