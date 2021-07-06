import logging
from typing import Optional

import pexpect

from .app import App
from .utils import ProcessContainer


class Dut(ProcessContainer):
    """
    Device under test (Dut) base class

    :ivar: app: :class:`pytest_embedded.app.App` instance
    :ivar: pexpect_proc: :class:`pexpect.spawn` instance
    """

    def __init__(self, app: Optional[App] = None, pexpect_proc: Optional[pexpect.spawn] = None, **kwargs) -> None:
        super().__init__()

        self.app = app
        self.pexpect_proc = pexpect_proc

        for k, v in kwargs.items():
            setattr(self, k, v)

    def write(self, *args, **kwargs) -> None:
        """
        Write to :attr:`pexpect_proc`. All arguments would pass to :func:`pexpect.spawn.write`
        """
        self.pexpect_proc.write(*args, **kwargs)

    def expect(self, *args, **kwargs) -> None:
        """
        Expect from :attr:`pexpect_proc`. All arguments would pass to :func:`pexpect.expect`
        """
        try:
            self.pexpect_proc.expect(*args, **kwargs)
        except (pexpect.EOF, pexpect.TIMEOUT):
            logging.error(f'Not found {args}, {kwargs}')
            raise
