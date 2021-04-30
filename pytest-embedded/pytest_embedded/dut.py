import io
import logging
import multiprocessing
from typing import Optional

import pexpect
from pytest_embedded.app import App


def bytes_to_str(byte_str: bytes) -> str:
    if not byte_str:
        return ''

    return '\n'.join([line.strip() for line in byte_str.decode('utf8', 'ignore').split('\r\n') if line.strip()])


class DUT:
    def __init__(self, app: Optional[App] = None, port: Optional[str] = None) -> None:
        self.app = app
        self.port = port

        # used for do expect str/regex from
        self.pexpect_proc = pexpect.spawn(['cat'], maxread=1000000)

        # forward_io_proc would get output from ``open_port_session``, do some pre-process jobs and then forward the
        # pre-processed output to the ``pexpect_proc``
        self.raw_output_session = self.open_port_session()
        self.forward_io_proc = self.get_forward_io_process()
        self.forward_io_proc.start()

    def close(self):
        try:
            self.forward_io_proc.terminate()
            self.raw_output_session.close()  # or other methods
            self.pexpect_proc.terminate(force=True)
        except Exception as e:  # noqa
            logging.error(e)

    def open_port_session(self) -> io.BytesIO:
        # provide a dummy one here, should be implemented by plugins
        return io.BytesIO()

    def pre_process(self, byte_str) -> str:
        if isinstance(byte_str, bytes):
            return byte_str.decode('ascii')
        return byte_str

    def get_forward_io_process(self) -> multiprocessing.Process:
        proc = multiprocessing.Process(target=self.forward_io)
        return proc

    def forward_io(self, breaker: bytes = b'\n'):
        while True:
            line = b''
            sess_output = self.raw_output_session.read()  # a single char
            while sess_output and sess_output != breaker:
                line += sess_output
                sess_output = self.raw_output_session.read()
            line += sess_output
            line = self.pre_process(line)
            self.pexpect_proc.write(line)

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
