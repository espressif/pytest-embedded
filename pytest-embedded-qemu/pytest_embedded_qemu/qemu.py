import os
import shlex
import typing as t

from pytest_embedded.log import DuplicateStdoutPopen

from . import DEFAULT_IMAGE_FN

if t.TYPE_CHECKING:
    from .app import QemuApp


class Qemu(DuplicateStdoutPopen):
    """
    QEMU class
    """

    SOURCE = 'QEMU'

    QEMU_PROG_PATH = 'qemu-system-xtensa'
    QEMU_PROG_FMT = 'qemu-system-{}'

    QEMU_DEFAULT_ARGS = '-nographic -machine esp32'
    QEMU_DEFAULT_FMT = '-nographic -machine {}'

    QEMU_STRAP_MODE_FMT = '-global driver=esp32.gpio,property=strap_mode,value={}'
    QEMU_SERIAL_TCP_FMT = '-serial tcp::{},server,nowait'

    def __init__(
        self,
        qemu_image_path: t.Optional[str] = None,
        qemu_prog_path: t.Optional[str] = None,
        qemu_cli_args: t.Optional[str] = None,
        qemu_extra_args: t.Optional[str] = None,
        app: t.Optional['QemuApp'] = None,
        **kwargs,
    ):
        """
        Args:
            qemu_image_path: QEMU image path
            qemu_prog_path: QEMU program path
            qemu_cli_args: QEMU CLI arguments
            qemu_extra_args: QEMU CLI extra arguments, will be appended to `qemu_cli_args`
        """
        self.app = app

        image_path = qemu_image_path or DEFAULT_IMAGE_FN
        if not os.path.exists(image_path):
            raise ValueError(f'QEMU image path doesn\'t exist: {image_path}')

        qemu_prog_path = qemu_prog_path or self.qemu_prog_name
        qemu_cli_args = shlex.split(qemu_cli_args or self.qemu_default_args)
        qemu_extra_args = shlex.split(qemu_extra_args or '')

        super().__init__(
            cmd=[qemu_prog_path, *qemu_cli_args, *qemu_extra_args] + ['-drive', f'file={image_path},if=mtd,format=raw'],
            **kwargs,
        )

    @property
    def qemu_prog_name(self):
        if self.app:
            try:
                return self.QEMU_PROG_FMT.format('xtensa' if self.app.is_xtensa else 'riscv32')
            except AttributeError:
                pass

        return self.QEMU_PROG_PATH

    @property
    def qemu_default_args(self):
        if self.app:
            try:
                return self.QEMU_DEFAULT_FMT.format(self.app.target)
            except AttributeError:
                pass

        return self.QEMU_DEFAULT_ARGS

    def _hard_reset(self):
        """
        This is a fake hard_reset. Keep this API to keep the consistency.
        """
        # TODO: implement with QMP
        #  https://gitlab.com/qemu-project/python-qemu-qmp/-/issues/6
        #  for now got so many unexpected exceptions while __del__
        raise NotImplementedError
