import asyncio
import binascii
import logging
import os
import shlex
import socket
import typing as t
from dataclasses import dataclass

from pytest_embedded.log import DuplicateStdoutPopen
from qemu.qmp import QMPClient

from . import DEFAULT_IMAGE_FN

if t.TYPE_CHECKING:
    from .app import QemuApp


@dataclass
class QemuTarget:
    strap_mode: str
    default_efuse: bytes


QEMU_TARGETS: dict[str, QemuTarget] = {
    'esp32': QemuTarget(
        strap_mode='0x0F',
        default_efuse=binascii.unhexlify(
            '00000000000000000000000000800000000000000000100000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000'
        ),
    ),
    'esp32c3': QemuTarget(
        strap_mode='0x02',
        default_efuse=binascii.unhexlify(
            '00000000000000000000000000000000000000000000000000000000000000000000000000000c00'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '000000000000000000000000000000000000000000000000'
        ),
    ),
    'esp32s3': QemuTarget(
        strap_mode='0x07',
        default_efuse=binascii.unhexlify(
            '00000000000000000000000000000000000000000000000000000000000000000000000000000c00'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '000000000000000000000000000000000000000000000000'
        ),
    ),
}


class Qemu(DuplicateStdoutPopen):
    """
    QEMU class
    """

    SOURCE = 'QEMU'

    QEMU_PROG_PATH = 'qemu-system-xtensa'

    QEMU_DEFAULT_ARGS = '-nographic -machine esp32'
    QEMU_DEFAULT_FMT = '-nographic -machine {}'

    QEMU_STRAP_MODE_FMT = 'driver={}.gpio,property=strap_mode,value={}'
    QEMU_SERIAL_TCP_FMT = '-serial tcp::{},server,nowait'
    QEMU_DEFAULT_QMP_FMT = '-qmp tcp:127.0.0.1:{},server,wait=off'

    def __init__(
        self,
        qemu_image_path: str | None = None,
        qemu_prog_path: str | None = None,
        qemu_cli_args: str | None = None,
        qemu_extra_args: str | None = None,
        qemu_efuse_path: str | None = None,
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
            raise ValueError(f"QEMU image path doesn't exist: {image_path}")

        self.qemu_prog_path = qemu_prog_path or self.qemu_prog_name
        self.image_path = image_path
        self.efuse_path = qemu_efuse_path

        if qemu_cli_args:
            qemu_cli_args = qemu_cli_args.strip('"').strip("'")
        qemu_cli_args = shlex.split(qemu_cli_args or self.qemu_default_args)
        qemu_extra_args = shlex.split(qemu_extra_args or '')

        if self.efuse_path:
            logging.debug('The eFuse file will be saved to: %s', self.efuse_path)
            with open(self.efuse_path, 'wb') as f:
                f.write(QEMU_TARGETS[self.app.target].default_efuse)
            qemu_extra_args += [
                '-global',
                self.QEMU_STRAP_MODE_FMT.format(self.app.target, QEMU_TARGETS[self.app.target].strap_mode),
                '-drive',
                f'file={self.efuse_path},if=none,format=raw,id=efuse',
                '-global',
                f'driver=nvram.{self.app.target}.efuse,property=drive,value=efuse',
            ]

        self.qmp_addr = None
        self.qmp_port = None

        dut_index = int(kwargs.pop('dut_index', 0))
        for i, v in enumerate(qemu_cli_args):
            if v == '-qmp':
                d = qemu_cli_args[i + 1]
                if not d.startswith('tcp'):
                    raise ValueError('Please use TCP for qmp, example: -qmp tcp:localhost:4488,server,wait=off')
                cmd = d.split(',')
                _, self.qmp_addr, self.qmp_port = cmd[0].split(':')
                self.qmp_port = int(self.qmp_port) + dut_index
                cmd[0] = f'tcp:{self.qmp_addr}:{self.qmp_port}'
                qemu_cli_args[i + 1] = ','.join(cmd)
                break
        else:
            self.qmp_addr = '127.0.0.1'
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.qmp_addr, 0))
                _, self.qmp_port = s.getsockname()
            qemu_cli_args += shlex.split(self.QEMU_DEFAULT_QMP_FMT.format(self.qmp_port))

        super().__init__(
            cmd=[
                self.qemu_prog_path,
                *qemu_cli_args,
                *qemu_extra_args,
                '-drive',
                f'file={image_path},if=mtd,format=raw',
            ],
            **kwargs,
        )

    def execute_efuse_command(self, command: str):
        import espefuse
        import pexpect

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            _, available_port = s.getsockname()

        run_qemu_command = [
            '-nographic',
            '-machine',
            self.app.target,
            '-drive',
            f'file={self.image_path},if=mtd,format=raw',
            '-global',
            self.QEMU_STRAP_MODE_FMT.format(self.app.target, QEMU_TARGETS[self.app.target].strap_mode),
            '-drive',
            f'file={self.efuse_path},if=none,format=raw,id=efuse',
            '-global',
            f'driver=nvram.{self.app.target}.efuse,property=drive,value=efuse',
            '-serial',
            f'tcp::{available_port},server,nowait',
        ]
        try:
            child = pexpect.spawn(self.qemu_prog_path, run_qemu_command)
            res = shlex.split(command)
            child.expect('qemu')

            res = [r for r in res if r != '--do-not-confirm']
            espefuse.main(
                [
                    '--port',
                    f'socket://localhost:{available_port}',
                    '--before',
                    'no-reset',
                    '--do-not-confirm',
                    *res,
                ]
            )
            self._hard_reset()
        finally:
            child.terminate()

    @property
    def qemu_prog_name(self):
        if self.app:
            return self.app.qemu_prog_path

        logging.warning('App not set, use default qemu program name "%s"', self.QEMU_DEFAULT_PROG_PATH)
        return self.QEMU_PROG_PATH

    @property
    def qemu_default_args(self):
        if self.app:
            try:
                return self.QEMU_DEFAULT_FMT.format(self.app.target)
            except AttributeError:
                pass

        return self.QEMU_DEFAULT_ARGS

    def qmp_execute_cmd(self, execute, arguments=None):
        response = None

        async def h_r():
            nonlocal response

            qmp = QMPClient()
            try:
                await qmp.connect((str(self.qmp_addr), int(self.qmp_port)))
                response = await qmp.execute(execute, arguments=arguments)
            finally:
                await qmp.disconnect()

        asyncio.run(h_r())
        return response

    def _hard_reset(self):
        self.qmp_execute_cmd('system_reset')

    def take_screenshot(self, image_path):
        self.qmp_execute_cmd('screendump', arguments={'filename': image_path})
