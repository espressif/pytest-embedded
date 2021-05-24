import logging
import sys
from functools import wraps
from typing import Optional

import pexpect
from pytest_embedded.app import App


def bytes_to_str(byte_str: bytes) -> str:
    if not byte_str:
        return ''

    return '\n'.join([line.strip() for line in byte_str.decode('utf-8', 'ignore').split('\r\n') if line.strip()])


class Dut:
    """
    Dut base class

    :ivar: pexpect_proc: :mod:`pexpect` process. would copy stdin to stdout. This could help to do
        :func:`pexpect.expect` over multi input resources
    """

    def __init__(self, app: Optional[App] = None, *args, **kwargs) -> None:
        self.app = app

        # used for do expect str/regex from
        # Here we can use self.pexpect_proc.write to send string to stdin, cat will copy the stdin to stdout
        self.pexpect_proc = pexpect.spawn(['cat'], maxread=1000000)

        # collects all the threads/processes need to be closed/terminated before getting destructed
        self._sessions_close_methods = [
            self.pexpect_proc.terminate,
        ]

        for k, v in kwargs.items():
            setattr(self, k, v)

    def close(self) -> None:
        """
        Call all the sessions/threads/processes terminate methods defined in :attr:`self._sessions_close_methods`
        """
        for func in self._sessions_close_methods:
            try:
                func()
            except Exception as e:
                logging.error(e)

    def expect(self, *args, **kwargs) -> None:
        """
        Call :func:`pexpect.expect` with the :attr:`pexpect_proc`, all arguments would pass to :func:`pexpect.expect`
        """

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

    def redirect_stdout(func):
        """
        This is a decorator which will redirect the stdout to the pexpect thread. Should be the outermost decorator
        if there are multi decorators
        """

        @wraps(func)
        def inner(self, *args, **kwargs):
            origin_stdout = sys.stdout
            sys.stdout = self.pexpect_proc

            try:
                res = func(self, *args, **kwargs)
            finally:
                sys.stdout = origin_stdout

            return res

        return inner
