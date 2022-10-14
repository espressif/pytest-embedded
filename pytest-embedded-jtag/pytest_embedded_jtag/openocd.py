import logging
import os
import shlex
import telnetlib
import time
from typing import AnyStr, Optional

from pytest_embedded.log import DuplicateStdoutPopen, MessageQueue
from pytest_embedded.utils import to_bytes, to_str


class OpenOcd(DuplicateStdoutPopen):
    """
    Class to communicate to OpenOCD
    """

    SOURCE = 'OPENOCD'

    OPENOCD_PROG_PATH = 'openocd'
    OPENOCD_DEFAULT_ARGS = '-f board/esp32-wrover-kit-3.3v.cfg'

    TCL_BASE_PORT = 6666
    TELNET_BASE_PORT = 4444
    GDB_BASE_PORT = 3333

    def __init__(
        self,
        msg_queue: MessageQueue,
        openocd_prog_path: Optional[str] = None,
        openocd_cli_args: Optional[str] = None,
        port_offset: int = 0,
        **kwargs,
    ):
        openocd_prog_path = openocd_prog_path or os.getenv('OPENOCD_BIN', self.OPENOCD_PROG_PATH)
        openocd_cli_args = shlex.split(openocd_cli_args or self.OPENOCD_DEFAULT_ARGS)

        openocd_scripts_path = os.getenv('OPENOCD_SCRIPTS')
        if openocd_scripts_path:
            openocd_cli_args.extend(['-s', openocd_scripts_path])

        self.tcl_port = self.TCL_BASE_PORT + port_offset
        self.telnet_port = self.TELNET_BASE_PORT + port_offset
        self.gdb_port = self.GDB_BASE_PORT + port_offset

        openocd_cli_args.extend(
            [
                '-c',
                f'tcl_port {self.tcl_port}',
                '-c',
                f'telnet_port {self.telnet_port}',
                '-c',
                f'gdb_port {self.gdb_port}',
            ]
        )

        cmd = [openocd_prog_path] + openocd_cli_args
        logging.info(' '.join(cmd))

        super().__init__(msg_queue, cmd, **kwargs)

        # open telnet port to interact with openocd
        for i in range(30):
            try:
                self.telnet = telnetlib.Telnet('127.0.0.1', self.telnet_port, 5)
                break
            except ConnectionRefusedError:
                time.sleep(1)
        else:
            raise ConnectionRefusedError

    def write(self, cmd: AnyStr) -> str:
        # read all output already sent
        resp = self.telnet.read_very_eager()

        logging.debug(f'TELNET ->: {cmd}')
        self.telnet.write(to_bytes(cmd, '\n'))

        resp = self.telnet.read_until(b'>')

        return to_str(resp)
