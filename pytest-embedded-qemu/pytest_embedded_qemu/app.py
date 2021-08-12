import os
from typing import Optional

import pexpect
from pytest_embedded.log import cls_redirect_stdout, live_print_call
from pytest_embedded_idf.app import IdfApp

from . import DEFAULT_IMAGE_FN


class IdfFlashImageMaker:
    """
    Create a single image for qemu based on the `IdfApp`'s partition table and all the flash files.
    """

    def __init__(self, app: IdfApp, image_path: str):
        """
        Args:
            app: `IdfApp` instance
            image_path: output image path
        """
        self.app = app
        self.image_path = image_path

    def make_bin(self) -> None:
        """
        Create a single image file for qemu.
        """
        # flash files is sorted, if the first offset is not 0x0, we need to fill in with empty bin
        if self.app.flash_files[0][0] != 0x0:
            self._write_empty_bin(count=self.app.flash_files[0][0])
        for offset, file_path, encrypted in self.app.flash_files:
            if encrypted:
                raise NotImplementedError('will implement later')
            else:
                self._write_bin(file_path, seek=offset)

    def _write_empty_bin(self, count: int, bs: int = 1024, seek: int = 0):
        live_print_call(
            f'dd if=/dev/zero bs={bs} count={count} seek={seek} of={self.image_path}',
            shell=True,
        )

    def _write_bin(self, binary_filepath, bs: int = 1, seek: int = 0):
        live_print_call(
            f'dd if={binary_filepath} bs={bs} seek={seek} of={self.image_path} conv=notrunc',
            shell=True,
        )

    def _write_encrypted_bin(self, binary_filepath, bs: int = 1, seek: int = 0):
        live_print_call(
            f'dd if=/dev/zero bs=1 count=32 of=key.bin',
            shell=True,
        )  # generate a fake key bin
        live_print_call(
            f'espsecure.py encrypt_flash_data --keyfile key.bin --output decrypted.bin --address {seek} '
            f'{binary_filepath}',
            shell=True,
        )
        self._write_bin('decrypted.bin', bs=bs, seek=seek)

    def _burn_efuse(self):
        pass


class QemuApp(IdfApp):
    """
    QEMU App class
    """

    def __init__(
        self,
        app_path: Optional[str] = None,
        part_tool: Optional[str] = None,
        qemu_image_path: Optional[str] = None,
        pexpect_proc: Optional[pexpect.spawn] = None,
        **kwargs,
    ):
        """
        Args:
            app_path: App path
            part_tool: Partition tool
            qemu_image_path: QEMU image path, would create with `IdfFlashImageMaker.make_bin()` if not exists.
            pexpect_proc: `PexpectProcess` instance
        """
        self.pexpect_proc = pexpect_proc
        self.image_path = qemu_image_path or os.path.join(app_path, DEFAULT_IMAGE_FN)

        super().__init__(app_path, part_tool, **kwargs)

        if self.target != 'esp32':
            raise ValueError('For now on QEMU we only support ESP32')

        self.create_image()

    @cls_redirect_stdout(source='create image')
    def create_image(self) -> None:
        """
        Create the image if not exists
        """
        if os.path.exists(self.image_path):
            print(f'Using image already exists: {self.image_path}')
        else:
            image_maker = IdfFlashImageMaker(self, self.image_path)
            image_maker.make_bin()
