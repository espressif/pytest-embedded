import telnetlib
from time import sleep
from typing import AnyStr

from pytest_embedded.utils import to_bytes
from pytest_embedded_serial.dut import SerialDut

from .gdb import Gdb
from .openocd import OpenOcd


class JtagDut(SerialDut):
    """
    JTAG DUT class

    Attributes:
        openocd (OpenOcd): `OpenOcd` instance
        gdb (Gdb): `Gdb` instance
        telnet (telnetlib.Telnet): telnet server instance
    """

    def __init__(
        self,
        openocd: OpenOcd,
        gdb: Gdb,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.openocd = openocd
        self.gdb = gdb

        sleep(1)  # make sure openocd already opened telnet port
        self.telnet = telnetlib.Telnet(self.openocd.TELNET_HOST, self.openocd.TELNET_PORT, 5)
        self.telnet.send = self.telnet_send  # bind send method

    def telnet_send(self, s: AnyStr) -> None:
        """
        Send commands through telnet port, could also be called by `self.telnet.send()`

        Args:
            s: `bytes` or `str`
        """
        self.telnet.write(to_bytes(s, '\n'))

    def close(self) -> None:
        self.telnet.close()

        super(JtagDut, self).close()
