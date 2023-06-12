import contextlib
import logging
import os
import typing as t

from pytest_embedded.log import MessageQueue, live_print_call
from pytest_embedded_idf.app import IdfApp

from . import DEFAULT_IMAGE_FN, ENCRYPTED_IMAGE_FN


class IdfFlashImageMaker:
    """
    Create a single image for QEMU based on the `IdfApp`'s partition table and all the flash files.
    """

    XTENSA_FLASH_BIN_SIZES = [
        (2 * 1024 * 1024, '2MB'),
        (4 * 1024 * 1024, '4MB'),
        (8 * 1024 * 1024, '8MB'),
        (16 * 1024 * 1024, '16MB'),
    ]

    RISCV_FLASH_BIN_SIZES = [
        (256 * 1024, '256KB'),
        (512 * 1024, '512KB'),
        (1 * 1024 * 1024, '1MB'),
        (2 * 1024 * 1024, '2MB'),
        (4 * 1024 * 1024, '4MB'),
        (8 * 1024 * 1024, '8MB'),
        (16 * 1024 * 1024, '16MB'),
        (32 * 1024 * 1024, '32MB'),
        (64 * 1024 * 1024, '64MB'),
        (128 * 1024 * 1024, '128MB'),
    ]

    def __init__(self, app: 'QemuApp', image_path: str):
        """
        Args:
            app: `IdfApp` instance
            image_path: output image path
        """
        self.app = app
        self.image_path = image_path

    def _get_upper_bound(self, size: int, ranges: t.List[t.Tuple[int, str]]) -> str:
        for r, s in ranges:
            if size <= r:
                upper = s
                break
        else:
            raise ValueError(f'Flash size {size} is too big for QEMU, max is {ranges[-1][1]}')

        return upper

    @property
    def qemu_flash_size(self):
        if self.app.flash_settings.get('flash_size') not in ['keep', 'detect']:
            # 2MB-c1, 4MB-ci
            return self.app.flash_settings['flash_size'].split('-')[0]

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
                'merge_bin',
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

    def __init__(
        self,
        msg_queue: MessageQueue,
        qemu_image_path: t.Optional[str] = None,
        skip_regenerate_image: t.Optional[bool] = False,
        encrypt: t.Optional[bool] = False,
        keyfile: t.Optional[str] = None,
        **kwargs,
    ):
        self._q = msg_queue

        super().__init__(**kwargs)

        self.image_path = qemu_image_path or os.path.join(self.binary_path, DEFAULT_IMAGE_FN)
        self.skip_regenerate_image = skip_regenerate_image
        self.encrypt = encrypt
        self.keyfile = keyfile

        if self.encrypt:
            self.encrypted_image_path = os.path.join(self.binary_path, ENCRYPTED_IMAGE_FN)

        self.create_image()

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
                image_maker = IdfFlashImageMaker(self, self.image_path)
                image_maker.make_bin()
