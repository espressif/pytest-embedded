from typing import TYPE_CHECKING, AnyStr, Optional

from pytest_embedded.dut import Dut
from pytest_embedded.utils import to_bytes

from .serial import Serial

if TYPE_CHECKING:
    from pytest_embedded_jtag import Gdb, OpenOcd, Telnet


class SerialDut(Dut):
    """
    Dut class for serial ports

    Attributes:
        serial (Serial): `Serial` instance
        openocd (OpenOcd): `OpenOcd` instance, applied only when `jtag` service is activated
        gdb (Gdb): `Gdb` instance, applied only when `jtag` service is activated
        telnet (Telnet): `Telnet` instance, applied only when `jtag` service is activated
    """

    def __init__(
        self,
        serial: Serial,
        openocd: Optional['OpenOcd'] = None,
        gdb: Optional['Gdb'] = None,
        telnet: Optional['Telnet'] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.serial = serial
        self.openocd = openocd
        self.gdb = gdb
        self.telnet = telnet

        self.setup_jtag()

    def write(self, data: AnyStr) -> None:
        self.serial.proc.write(to_bytes(data, '\n'))

    def setup_jtag(self):
        if self.gdb:
            self.gdb.write('set remotetimeout 10')
            self.gdb.write(f'target extended-remote :{self.openocd.gdb_port}')
