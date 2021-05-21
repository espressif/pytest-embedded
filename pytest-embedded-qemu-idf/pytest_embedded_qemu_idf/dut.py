import os
import subprocess
import sys
from typing import Optional

from pytest_embedded.dut import Dut
from pytest_embedded_idf.app import IdfApp


class FlashImageMaker:
    """
    Create a single image for qemu based on the :class:`pytest-embedded-idf.app.IdfApp`'s partition
    table and all the flash files.

    :ivar: app: :class:`pytest-embedded-idf.app.IdfApp` instance
    :ivar: qemu_image_path: output image path, would create `flash_image.bin` under the work dir if not set.
    """

    def __init__(self, app: IdfApp, qemu_image_path: Optional[str] = None):
        self.app = app
        self.qemu_image_path = qemu_image_path or 'flash_image.bin'

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
        subprocess.run(f'dd if=/dev/zero bs={bs} count={count} seek={seek} of={self.output_filepath}',
                       shell=True, stdout=sys.stdout, stderr=sys.stdout)

    def _write_bin(self, binary_filepath, bs: int = 1, seek: int = 0):
        subprocess.run(f'dd if={binary_filepath} bs={bs} seek={seek} of={self.output_filepath} conv=notrunc',
                       shell=True, stdout=sys.stdout, stderr=sys.stdout)

    def _write_encrypted_bin(self, binary_filepath, bs: int = 1, seek: int = 0):
        subprocess.run(f'dd if=/dev/zero bs=1 count=32 of=key.bin',
                       shell=True, stdout=sys.stdout, stderr=sys.stdout)  # generate a fake key bin
        subprocess.run(f'espsecure.py encrypt_flash_data --keyfile key.bin --output decrypted.bin --address {seek} '
                       f'{binary_filepath}', shell=True, stdout=sys.stdout, stderr=sys.stdout)
        self._write_bin('decrypted.bin', bs=bs, seek=seek)

    def _burn_efuse(self):
        pass


class IdfQemuDut(Dut):
    """
    IDF QEMU dut class

    :ivar: qemu_prog: QEMU executable path, default value: ``QEMU_PROG``
    :ivar: qemu_cli_args: QEMU CLI options, default value: ``QEMU_CLI_ARGS``
    :ivar: qemu_image_path: QEMU single image path, default value: ``QEMU_IMAGE_PATH``.
        would generate one if not exists
    """
    QEMU_PROG = 'qemu-system-xtensa'
    QEMU_CLI_ARGS = '-nographic -no-reboot -machine esp32'
    QEMU_IMAGE_PATH = 'flash_image.bin'

    def __init__(self,
                 app: Optional[IdfApp] = None,
                 qemu_prog: Optional[str] = None,
                 qemu_cli_args: Optional[str] = None,
                 qemu_image_path: Optional[str] = None,
                 *args, **kwargs) -> None:
        super().__init__(app, *args, **kwargs)

        if getattr(self.app, 'target', None) != 'esp32':
            raise NotImplementedError('For now we only support target esp32')

        self.qemu_prog = qemu_prog or self.QEMU_PROG
        self.qemu_cli_args = qemu_cli_args or self.QEMU_CLI_ARGS
        self.qemu_image_path = qemu_image_path or self.QEMU_IMAGE_PATH
        self.qemu_image_args = f'-drive file={self.qemu_image_path},if=mtd,format=raw'

        self._start()

    @Dut.redirect_stdout
    def _start(self):
        if not os.path.isfile(self.qemu_image_path):
            image_maker = FlashImageMaker(self.app, self.qemu_image_path)
            image_maker.make_bin()
        subprocess.Popen(f'{self.QEMU_PROG} {self.qemu_cli_args} {self.qemu_image_args}',
                         shell=True, stdout=sys.stdout, stderr=sys.stdout)
