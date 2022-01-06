import functools
import logging
from typing import AnyStr, Callable, Match, Union

import pexpect

from .app import App
from .log import PexpectProcess
from .utils import ProcessContainer


class Dut(ProcessContainer):
    """
    Device under test (DUT) base class
    """

    def __init__(self, pexpect_proc: PexpectProcess, app: App, **kwargs) -> None:
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            app: `App` instance
        """
        super().__init__()

        self.pexpect_proc = pexpect_proc
        self.app = app

        for k, v in kwargs.items():
            setattr(self, k, v)

    def write(self, *args, **kwargs) -> None:
        """
        Write to `pexpect_proc`. All arguments would pass to `pexpect.spawn.write()`
        """
        self.pexpect_proc.write(*args, **kwargs)

    def _pexpect_func(func) -> Callable[..., Union[Match, AnyStr]]:  # noqa
        @functools.wraps(func)  # noqa
        def wrapper(self, *args, **kwargs) -> Union[Match, AnyStr]:
            try:
                func(self, *args, **kwargs)  # noqa
            except (pexpect.EOF, pexpect.TIMEOUT):
                logging.error(f'Not found {args}, {kwargs}')
                logging.error(f'Bytes in buffer:\n{self.pexpect_proc.buffer}')
                raise
            else:
                if self.pexpect_proc.match in [pexpect.EOF, pexpect.TIMEOUT]:
                    return self.pexpect_proc.before.rstrip()

                return self.pexpect_proc.match

        return wrapper

    @_pexpect_func  # noqa
    def expect(self, *args, **kwargs) -> None:
        """
        Expect from `pexpect_proc`. All the arguments would pass to `pexpect.expect()`.

        Returns:
            AnyStr: if you're matching pexpect.EOF or pexpect.TIMEOUT to get all the current buffers.

        Returns:
            re.Match: if matched given string.
        """
        self.pexpect_proc.expect(*args, **kwargs)

    @_pexpect_func  # noqa
    def expect_exact(self, *args, **kwargs) -> None:
        """
        Expect from `pexpect_proc`. All the arguments would pass to `pexpect.expect_exact()`.

        Returns:
            AnyStr: if you're matching pexpect.EOF or pexpect.TIMEOUT to get all the current buffers.

        Returns:
            re.Match: if matched given string.
        """
        self.pexpect_proc.expect_exact(*args, **kwargs)

    @_pexpect_func  # noqa
    def expect_list(self, *args, **kwargs) -> None:
        """
        Expect from `pexpect_proc`. All the arguments would pass to `pexpect.expect_list()`.

        Returns:
            AnyStr: if you're matching pexpect.EOF or pexpect.TIMEOUT to get all the current buffers.

        Returns:
            re.Match: if matched given compiled regex.

        Notes:
            For the first argument, which is the regex list, you should pass the compiled regex with bytes.

            For example, could pass `[re.compile(b'foo'), re.compile(b'bar')]`
        """
        self.pexpect_proc.expect_list(*args, **kwargs)
