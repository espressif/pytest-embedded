import logging
from typing import AnyStr

from pytest_embedded.dut import Dut
from pytest_embedded.utils import to_bytes

from .serial import Serial


class SerialDut(Dut):
    """
    Dut class for serial ports

    Attributes:
        serial (Serial): `Serial` instance
    """

    def __init__(self, serial: Serial, **kwargs) -> None:
        super().__init__(**kwargs)

        self.serial = serial

    def write(self, data: AnyStr) -> None:
        return self._q.put(to_bytes(data, '\n'))

    def close(self) -> None:
        self.serial.close()

        self.serial.occupied_ports.pop(self.serial.port, None)
        logging.debug(f'released {self.serial.port}')

        super().close()
