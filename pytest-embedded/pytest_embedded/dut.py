import logging
from typing import Optional

import pexpect
from pytest_embedded.app import App


def bytes_to_str(byte_str: bytes) -> str:
    if not byte_str:
        return ''

    return '\n'.join([line.strip() for line in byte_str.decode('utf8', 'ignore').split('\r\n') if line.strip()])


class Dut:
    def __init__(self, app: Optional[App] = None, *args, **kwargs) -> None:
        self.app = app

        # used for do expect str/regex from
        # Here we can use self.pexpect_proc.write to send string to stdin, cat will copy the stdin to stdout
        self.pexpect_proc = pexpect.spawn(['cat'], maxread=1000000)

        # collects all the threads/processes need to be closed/terminated before getting destructed
        self._sessions_close_methods = [
            self.pexpect_proc.terminate,
        ]

    def close(self):
        for func in self._sessions_close_methods:
            try:
                func()
            except Exception as e:
                logging.error(e)

    def expect(self, *args, **kwargs):
        log_level = logging.ERROR
        try:
            self.pexpect_proc.expect(*args, **kwargs)
        except (pexpect.EOF, pexpect.TIMEOUT):
            raise
        else:
            log_level = logging.INFO
        finally:
            logging.log(log_level, f'Buffered bytes:\n'
                                   f'{bytes_to_str(self.pexpect_proc.before)}')
