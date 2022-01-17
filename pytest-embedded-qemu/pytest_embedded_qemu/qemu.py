import logging
import os
from typing import Optional

from pytest_embedded.log import DuplicateStdoutPopen

from . import DEFAULT_IMAGE_FN


class Qemu(DuplicateStdoutPopen):
    """
    QEMU class
    """

    QEMU_PROG_PATH = 'qemu-system-xtensa'
    QEMU_DEFAULT_ARGS = '-nographic -no-reboot -machine esp32'

    QEMU_STRAP_MODE_FMT = '-global driver=esp32.gpio,property=strap_mode,value={}'
    QEMU_SERIAL_TCP_FMT = '-serial tcp::{},server,nowait'

    def __init__(
        self,
        qemu_image_path: Optional[str] = None,
        qemu_prog_path: Optional[str] = None,
        qemu_cli_args: Optional[str] = None,
        qemu_extra_args: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            qemu_image_path: QEMU image path
            qemu_prog_path: QEMU program path
            qemu_cli_args: QEMU CLI arguments
            qemu_extra_args: QEMU CLI extra arguments, will be appended to `qemu_cli_args`
        """
        image_path = qemu_image_path or DEFAULT_IMAGE_FN
        if not os.path.exists(image_path):
            raise ValueError(f'QEMU image path doesn\'t exist: {image_path}')

        qemu_prog_path = qemu_prog_path or self.QEMU_PROG_PATH
        qemu_cli_args = qemu_cli_args or self.QEMU_DEFAULT_ARGS

        qemu_extra_args = qemu_extra_args.replace('"', '') if qemu_extra_args else qemu_extra_args
        qemu_extra_args = [qemu_extra_args] if qemu_extra_args else []
        qemu_extra_args.append(f'-drive file={image_path},if=mtd,format=raw')

        cmd = f'{qemu_prog_path} {qemu_cli_args} {" ".join(qemu_extra_args)}'
        logging.debug(cmd)

        super().__init__(cmd, shell=True, **kwargs)
