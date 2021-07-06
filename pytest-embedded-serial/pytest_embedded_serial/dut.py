from typing import Optional

import pexpect
from pytest_embedded.app import App
from pytest_embedded.dut import Dut

from .serial import Serial


class SerialDut(Dut):
    """
    Dut class for serial ports

    :ivar: serial: :class:`Serial` instance
    :ivar: app: :class:`pytest_embedded.app.App` instance
    :ivar: pexpect_proc: :class:`pexpect.spawn` instance
    """

    def __init__(
        self, serial: Serial = None, app: Optional[App] = None, pexpect_proc: Optional[pexpect.spawn] = None, **kwargs
    ) -> None:
        super().__init__(app, pexpect_proc, **kwargs)

        self.serial = serial
        self.serial.create_forward_io_process(self.pexpect_proc, source='serial')

        self.proc_close_methods.append(self.serial.close)

    def write(self, data: bytes) -> int:
        return self.serial.proc.write(data)
