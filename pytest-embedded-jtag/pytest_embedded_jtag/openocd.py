import logging
import os
import shlex
from typing import Optional

from pytest_embedded.log import DuplicateStdoutPopen, MessageQueue


class OpenOcd(DuplicateStdoutPopen):
    """
    Class to communicate to OpenOCD
    """

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
