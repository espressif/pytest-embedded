import telnetlib
from time import sleep
from typing import Union

from pytest_embedded.app import App
from pytest_embedded.log import PexpectProcess
from pytest_embedded.utils import to_bytes
from pytest_embedded_serial.dut import SerialDut
from pytest_embedded_serial.serial import Serial

from .gdb import Gdb
from .openocd import OpenOcd


class JtagDut(SerialDut):
    """
    JTAG DUT class

    Attributes:
        telnet (telnetlib.Telnet): telnet server instance
    """

    def __init__(
        self,
        pexpect_proc: PexpectProcess,
        app: App,
        serial: Serial,
        openocd: OpenOcd,
        gdb: Gdb,
        **kwargs,
    ) -> None:
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            app: `App` instance
            serial: `Serial` instance
            openocd: `OpenOcd` instance
            gdb: `Gdb` instance
        """
        super().__init__(pexpect_proc, app, serial, **kwargs)
        self.openocd = openocd
        self.gdb = gdb

        sleep(10)  # make sure openocd already opened telnet port
        self.telnet = telnetlib.Telnet(self.openocd.TELNET_HOST, self.openocd.TELNET_PORT, 5)
        self.telnet.send = self.telnet_send  # type: ignore # bind send method.

        self.proc_close_methods.extend(
            [
                self.openocd.terminate,
                self.gdb.terminate,
                self.telnet.close,
            ]
        )

    def telnet_send(self, s: Union[bytes, str]) -> None:
        """
        Send commands through telnet port, could also be called by `self.telnet.send()`

        Args:
            s: `bytes` or `str`
        """
        self.telnet.write(to_bytes(s, '\n'))
