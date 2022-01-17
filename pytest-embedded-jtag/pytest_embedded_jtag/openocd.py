import logging
import os
from typing import Optional

from pytest_embedded.log import DuplicateStdoutPopen


class OpenOcd(DuplicateStdoutPopen):
    """
    Class to communicate to OpenOCD
    """

    OPENOCD_PROG_PATH = 'openocd'
    OPENOCD_DEFAULT_ARGS = '-f board/esp32-wrover-kit-3.3v.cfg -d2'

    TELNET_HOST = '127.0.0.1'
    TELNET_PORT = 4444

    def __init__(self, openocd_prog_path: Optional[str] = None, openocd_cli_args: Optional[str] = None, **kwargs):
        """
        Args:
            openocd_prog_path: openocd program path
            openocd_cli_args: openocd cli arguments
        """
        openocd_prog_path = openocd_prog_path or os.getenv('OPENOCD_BIN', self.OPENOCD_PROG_PATH)
        openocd_cli_args = openocd_cli_args or self.OPENOCD_DEFAULT_ARGS

        openocd_scripts_path = os.getenv('OPENOCD_SCRIPTS')
        if openocd_scripts_path:
            openocd_cli_args += f' -s {openocd_scripts_path}'

        cmd = f'{openocd_prog_path} {openocd_cli_args}'
        logging.info(cmd)

        super().__init__(cmd, shell=True, **kwargs)
