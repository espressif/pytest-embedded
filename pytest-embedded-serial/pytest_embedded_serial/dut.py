from typing import Optional

import pexpect
from pytest_embedded.app import App
from pytest_embedded.dut import Dut

from .serial import Serial


class SerialDut(Dut):
    """
    Dut class for serial ports
    """

    def __init__(
        self, serial: Serial = None, app: Optional[App] = None, pexpect_proc: Optional[pexpect.spawn] = None, **kwargs
    ) -> None:
        """
        Args:
            serial: `Serial` instance
            app: `App` instance
            pexpect_proc: `PexpectProcess` instance
        """
        super().__init__(app, pexpect_proc, **kwargs)

        self.serial = serial
        self.serial.create_forward_io_process(self.pexpect_proc, source='serial')

        self.proc_close_methods.append(self.serial.close)

    def write(self, data: bytes) -> int:
        return self.serial.proc.write(data)
