import logging
from typing import Optional

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

    def expect(self, *args, **kwargs) -> None:
        """
        Expect from `pexpect_proc`. All arguments would pass to `pexpect.expect()`
        """
        try:
            self.pexpect_proc.expect(*args, **kwargs)
        except (pexpect.EOF, pexpect.TIMEOUT):
            logging.error(f'Not found {args}, {kwargs}')
            raise
