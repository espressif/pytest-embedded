import logging
import re
import shlex
import time
from typing import AnyStr

from pytest_embedded.log import DuplicateStdoutPopen


class Gdb(DuplicateStdoutPopen):
    SOURCE = 'GDB'
    REDIRECT_CLS = None

    GDB_PROG_PATH = 'xtensa-esp32-elf-gdb'
    GDB_DEFAULT_ARGS = '--quiet'

    _GDB_RESPONSE_FINISHED_RE = re.compile(r'^\(gdb\)\s*$')

    def __init__(self, gdb_prog_path: str | None = None, gdb_cli_args: str | None = None, **kwargs):
        gdb_prog_path = gdb_prog_path or self.GDB_PROG_PATH
        gdb_cli_args = shlex.split(gdb_cli_args or self.GDB_DEFAULT_ARGS)

        self._gdb_first_write = True

        super().__init__(cmd=[gdb_prog_path, *gdb_cli_args], **kwargs)

    def write(self, s: AnyStr, non_blocking: bool = False, timeout: float = 30) -> str | None:
        with open(self._logfile) as fr:
            if self._gdb_first_write:
                # Discard all queued responses before the first write
                _ = fr.readlines()
                self._logfile_offset = fr.tell()
                self._gdb_first_write = False

            super().write(s)

            if non_blocking:
                logging.debug('non-blocking write...')
                return None

            _buffer = ''
            _t_start = time.time()
            fr.seek(self._logfile_offset)
            while True:
                line = fr.readline()
                if line:
                    _buffer += line
                    if self._GDB_RESPONSE_FINISHED_RE.match(line):
                        break

                _t_now = time.time()
                if (_t_now - _t_start) >= timeout:
                    logging.debug(f'current buffer: {_buffer}')
                    raise ValueError(f'gdb no response after {timeout} seconds')

            self._logfile_offset = fr.tell()

        logging.debug(f'{self.SOURCE} <-: {_buffer}')
        return _buffer
