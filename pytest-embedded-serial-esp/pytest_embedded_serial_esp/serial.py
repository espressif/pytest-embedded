import logging
from typing import Optional

import esptool
import pexpect
from pytest_embedded.app import App
from pytest_embedded.log import DuplicateStdout
from pytest_embedded_serial.dut import Serial


class EspSerial(Serial):
    """
    Serial class for ports connected to espressif products

    Attributes:
        esp: esptool.ESPLoader, will auto upload stub.
    """

    def __init__(
        self,
        target: Optional[App] = None,
        port: Optional[str] = None,
        pexpect_proc: Optional[pexpect.spawn] = None,
        **kwargs,
    ) -> None:

        self.pexpect_proc = pexpect_proc  # let the pexpect_proc work in `detect_target_port()` as well

        if port is None:
            ports = esptool.get_port_list()
        else:
            ports = [port]

        with DuplicateStdout(self.pexpect_proc, 'detecting port'):
            self.esp: esptool.ESPLoader = esptool.get_default_connected_device(
                ports, port=port, connect_attempts=3, initial_baud=self.DEFAULT_PORT_CONFIG['baudrate'], chip=target
            )
            self.esp = self.esp.run_stub()

        target = self.esp.CHIP_NAME.lower().replace('-', '')
        port = self.esp.serial_port
        logging.info(f'Target: {target}, Port: {port}')

        self.target = target
        super().__init__(port, pexpect_proc, **kwargs)

    def _start(self):
        self.esp.hard_reset()
