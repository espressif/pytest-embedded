import re
import shlex
from typing import AnyStr, Optional

from pytest_embedded.log import DuplicateStdoutPopen


class Gdb(DuplicateStdoutPopen):
    SOURCE = 'GDB'
    REDIRECT_CLS = None

    GDB_PROG_PATH = 'xtensa-esp32-elf-gdb'
    GDB_DEFAULT_ARGS = '--quiet'

    _GDB_RESPONSE_FINISHED_RE = re.compile(r'^\(gdb\)\s*$')

    def __init__(self, gdb_prog_path: Optional[str] = None, gdb_cli_args: Optional[str] = None, **kwargs):
        gdb_prog_path = gdb_prog_path or self.GDB_PROG_PATH
        gdb_cli_args = shlex.split(gdb_cli_args or self.GDB_DEFAULT_ARGS)

        self._gdb_first_prompt_matched = False

        super().__init__(cmd=[gdb_prog_path] + gdb_cli_args, **kwargs)

    def write(self, s: AnyStr, non_blocking: bool = False, timeout: float = 30) -> None:
        super().write(s)
