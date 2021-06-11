import datetime
import os
import subprocess
import tempfile
from typing import Optional

from pytest_embedded.log import live_print_call
from pytest_embedded_idf.app import IdfApp


class IdfFlashImageMaker:
    """
    Create a single image for qemu based on the :class:`pytest_embedded_idf.app.IdfApp`'s partition
    table and all the flash files.

    :ivar: app: :class:`pytest_embedded_idf.app.IdfApp` instance
    :ivar: flash_image_path: output image path, would create with :meth:`make_bin` if not set.
    """

    def __init__(self, app: IdfApp, flash_image_path: str):
        self.app = app
        self.flash_image_path = flash_image_path

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
            f'dd if=/dev/zero bs={bs} count={count} seek={seek} of={self.flash_image_path}',
            shell=True,
        )

    def _write_bin(self, binary_filepath, bs: int = 1, seek: int = 0):
        live_print_call(
            f'dd if={binary_filepath} bs={bs} seek={seek} of={self.flash_image_path} conv=notrunc',
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


class IdfQemu:
    """
    :ivar: image_path: image path that uses to run QEMU
    :ivar: qemu_inst: ``subprocess.Popen`` process which runs QEMU program
    :ivar: log_file: serial log filepath
    :ivar: cmd: cmd arguments that uses to run QEMU
    """

    QEMU_PROG_PATH = 'qemu-system-xtensa'
    QEMU_DEFAULT_ARGS = '-nographic -no-reboot -machine esp32'
    QEMU_SKIP_RUN_BOOT_ARGS = '-global driver=esp32.gpio,property=strap_mode,value=0x0f'

    def __init__(
        self,
        app: IdfApp,
        qemu_image_path: str,
        qemu_prog_path: Optional[str] = None,
        qemu_cli_args: Optional[str] = None,
        qemu_extra_args: Optional[str] = None,
        qemu_log_path: Optional[str] = None,
        qemu_skip_autorun: bool = False,
    ):
        if not qemu_image_path:
            raise ValueError('Required: qemu_image_path')

        self.app = app
        self.image_path = qemu_image_path

        qemu_prog_path = qemu_prog_path or self.QEMU_PROG_PATH
        qemu_cli_args = qemu_cli_args or self.QEMU_DEFAULT_ARGS

        qemu_extra_args = [qemu_extra_args] if qemu_extra_args else []
        qemu_extra_args.append(f'-drive file={qemu_image_path},if=mtd,format=raw')

        # we use log file to record serial output
        self.log_file = qemu_log_path or os.path.join(
            tempfile.tempdir, datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S'), 'serial.log'
        )
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        qemu_extra_args.append(f'-serial file:{self.log_file}')

        if qemu_skip_autorun:
            qemu_extra_args.append(self.QEMU_SKIP_RUN_BOOT_ARGS)

        self.qemu_inst = None
        self.cmd = f'{qemu_prog_path} {qemu_cli_args} {" ".join(qemu_extra_args)}'

    def __del__(self):
        self.close()

    def close(self) -> None:
        """
        Close the QEMU process
        """
        self.qemu_inst.terminate()

    def create_image(self) -> None:
        """
        Create the image if not exists
        """
        if self.app:
            if os.path.exists(self.image_path):
                print(f'Using image already exists: {self.image_path}')
            else:
                image_maker = IdfFlashImageMaker(self.app, self.image_path)
                image_maker.make_bin()

    def start(self) -> None:
        """
        Start the QEMU process
        """
        print(f'{self.cmd}')
        self.qemu_inst = subprocess.Popen(
            self.cmd,
            shell=True,
        )
