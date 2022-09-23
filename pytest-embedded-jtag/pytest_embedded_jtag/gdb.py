import logging
import shlex
from typing import Optional

from pytest_embedded.log import DuplicateStdoutPopen, MessageQueue


class Gdb(DuplicateStdoutPopen):
    GDB_PROG_PATH = 'xtensa-esp32-elf-gdb'
    GDB_DEFAULT_ARGS = '--quiet'

    def __init__(
        self, msg_queue: MessageQueue, gdb_prog_path: Optional[str] = None, gdb_cli_args: Optional[str] = None, **kwargs
    ):
        gdb_prog_path = gdb_prog_path or self.GDB_PROG_PATH
        gdb_cli_args = shlex.split(gdb_cli_args or self.GDB_DEFAULT_ARGS)

        cmd = [gdb_prog_path] + gdb_cli_args
        logging.info(' '.join(cmd))

        super().__init__(msg_queue, cmd, **kwargs)
