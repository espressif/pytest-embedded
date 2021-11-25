import logging
from typing import AnyStr, Match, Optional, Union

import pexpect

from .app import App
from .log import PexpectProcess
from .utils import ProcessContainer


class Dut(ProcessContainer):
    """
    Device under test (DUT) base class
    """

    def __init__(self, app: Optional[App] = None, pexpect_proc: Optional[PexpectProcess] = None, **kwargs) -> None:
        """
        Args:
            app: `App` instance
            pexpect_proc: `PexpectProcess` instance
        """
        super().__init__()

        self.app = app
        self.pexpect_proc = pexpect_proc

        for k, v in kwargs.items():
            setattr(self, k, v)

    def write(self, *args, **kwargs) -> None:
        """
        Write to `pexpect_proc`. All arguments would pass to `pexpect.spawn.write()`
        """
        self.pexpect_proc.write(*args, **kwargs)

    def expect(self, *args, **kwargs) -> Union[Match, AnyStr]:
        """
        Expect from `pexpect_proc`. All the arguments would pass to `pexpect.expect()`.

        Returns:
            AnyStr: if you're matching pexpect.EOF or pexpect.TIMEOUT to get all the current buffers.

        Returns:
            re.Match: if matched given string.
        """
        try:
            self.pexpect_proc.expect(*args, **kwargs)
        except (pexpect.EOF, pexpect.TIMEOUT):
            logging.error(f'Not found {args}, {kwargs}')
            raise
        else:
            if self.pexpect_proc.match in [pexpect.EOF, pexpect.TIMEOUT]:
                return self.pexpect_proc.before.rstrip()

            return self.pexpect_proc.match

    def expect_exact(self, *args, **kwargs) -> Union[Match, AnyStr]:
        """
        Expect from `pexpect_proc`. All the arguments would pass to `pexpect.expect_exact()`.

        Returns:
            AnyStr: if you're matching pexpect.EOF or pexpect.TIMEOUT to get all the current buffers.

        Returns:
            re.Match: if matched given string.
        """
        try:
            self.pexpect_proc.expect_exact(*args, **kwargs)
        except (pexpect.EOF, pexpect.TIMEOUT):
            logging.error(f'Not found {args}, {kwargs}')
            raise
        else:
            if self.pexpect_proc.match in [pexpect.EOF, pexpect.TIMEOUT]:
                return self.pexpect_proc.before.rstrip()

            return self.pexpect_proc.match

    def expect_list(self, *args, **kwargs) -> Union[Match, AnyStr]:
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
        try:
            self.pexpect_proc.expect_list(*args, **kwargs)
        except (pexpect.EOF, pexpect.TIMEOUT):
            logging.error(f'Not found {args}, {kwargs}')
            raise
        else:
            if self.pexpect_proc.match in [pexpect.EOF, pexpect.TIMEOUT]:
                return self.pexpect_proc.before.rstrip()

            return self.pexpect_proc.match
