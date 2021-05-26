import logging
from functools import wraps
from typing import Optional

import pexpect
from pytest_embedded.app import App
from pytest_embedded.log import DuplicateLogStdout


def bytes_to_str(byte_str: bytes) -> str:
    if not byte_str:
        return ''

    return '\n'.join([line.strip() for line in byte_str.decode('utf-8', 'ignore').split('\r\n') if line.strip()])


class Dut:
    """
    Dut base class

    :ivar: pexpect_proc: :mod:`pexpect` process. would copy stdin to stdout. This could help to do
        :func:`pexpect.expect` over multi input resources
    :ivar: app: :class:`pytest_embedded.app.App` or derived class instance
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
        try:
            self.pexpect_proc.expect(*args, **kwargs)
        except (pexpect.EOF, pexpect.TIMEOUT):
            logging.error(f'Not found {args}, {kwargs}')
            raise

    def redirect_stdout(source=None):
        """
        This is a decorator which will redirect the stdout to the pexpect thread. Should be the outermost decorator
        if there are multi decorators.

        :warning: within this decorator, the ``print`` function would be redirect to the
            :func:`pytest_embedded.log.DuplicateLogStdout.write`. All the ``args`` and ``kwargs`` passed to ``print``
            will be ignored.

        :attr: source: optional prefix of the log
        """

        def decorator(func):
            @wraps(func)
            def inner(self, *args, **kwargs):
                pexpect_proc = getattr(self, 'pexpect_proc', None)
                with DuplicateLogStdout(pexpect_proc, source):
                    res = func(self, *args, **kwargs)

                return res

            return inner

        return decorator
