import logging
import re
import shlex
import time
from typing import AnyStr, Optional

from pytest_embedded.log import DuplicateStdoutPopen, MessageQueue


class Gdb(DuplicateStdoutPopen):
    SOURCE = 'GDB'
    REDIRECT_CLS = None

    GDB_PROG_PATH = 'xtensa-esp32-elf-gdb'
    GDB_DEFAULT_ARGS = '--quiet'

    _GDB_RESPONSE_FINISHED_RE = re.compile(r'^\(gdb\)\s*$')

    def __init__(
        self, msg_queue: MessageQueue, gdb_prog_path: Optional[str] = None, gdb_cli_args: Optional[str] = None, **kwargs
    ):
        gdb_prog_path = gdb_prog_path or self.GDB_PROG_PATH
        gdb_cli_args = shlex.split(gdb_cli_args or self.GDB_DEFAULT_ARGS)

        cmd = [gdb_prog_path] + gdb_cli_args
        logging.info(' '.join(cmd))

        self._gdb_first_prompt_matched = False

        super().__init__(msg_queue, cmd, **kwargs)

    def write(self, s: AnyStr, non_blocking: bool = False, timeout: int = 30) -> Optional[str]:
        super().write(s)
        _buffer = ''
        _t_start = time.time()

        with open(self._logfile) as fr:
            fr.seek(self._logfile_offset)
            while True:
                line = fr.readline()
                _t_now = time.time()
                if non_blocking:
                    logging.debug('non-blocking write...')
                    return None

                if (_t_now - _t_start) >= timeout:
                    logging.debug(f'current buffer: {_buffer}')
                    raise ValueError(f'gdb no response after {timeout} seconds')

                if line:
                    _buffer += line
                    if self._GDB_RESPONSE_FINISHED_RE.match(line):
                        if not self._gdb_first_prompt_matched:
                            self._gdb_first_prompt_matched = True
                            continue
                        break

            self._logfile_offset = fr.tell()

        logging.debug(f'{self.SOURCE} <-: {_buffer}')
        return _buffer
