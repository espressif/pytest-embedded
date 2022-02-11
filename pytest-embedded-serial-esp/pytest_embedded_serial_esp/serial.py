import functools
import logging
from typing import Optional

import esptool
from pytest_embedded.log import DuplicateStdout, PexpectProcess
from pytest_embedded_serial.dut import Serial


class EspSerial(Serial):
    """
    Serial class for ports connected to espressif products

    Attributes:
        esp: esptool.ESPLoader, will auto upload stub.
    """

    DEFAULT_BAUDRATE = 115200

    def __init__(
        self,
        pexpect_proc: PexpectProcess,
        target: Optional[str] = None,
        port: Optional[str] = None,
        baud: int = DEFAULT_BAUDRATE,
        skip_autoflash: bool = False,
        **kwargs,
    ) -> None:
        if port is None:
            available_ports = esptool.get_port_list()
            ports = list(set(available_ports) - set(self.occupied_ports.keys()))
            logging.debug(f'Detecting ports from {", ".join(ports)}')
        else:
            ports = [port]

        with DuplicateStdout(pexpect_proc):
            initial_baud = min(self.DEFAULT_BAUDRATE, baud)  # don't sync faster than the default baud rate
            # normal loader
            self.esp: esptool.ESPLoader = esptool.get_default_connected_device(
                ports, port=port, connect_attempts=3, initial_baud=initial_baud, chip=target
            )
            if not self.esp:
                raise ValueError('Couldn\'t auto detect chip. Please manually specify with "--port"')

            # stub loader has more functionalities, need to run after calling `run_stub()`
            self.stub: esptool.ESPLoader = None  # type: ignore

            if baud > initial_baud:
                self.esp.change_baud(baud)  # change back to the users settings

        target = self.esp.CHIP_NAME.lower().replace('-', '')
        logging.info(f'Target: {target}, Port: {self.esp.serial_port}')

        self.target = target
        self.skip_autoflash = skip_autoflash
        super().__init__(pexpect_proc, port=self.esp._port, **kwargs)

    def use_esptool(func):
        """
        1. close the port and open the port to kill the `self._forward_io` thread
        2. call `run_stub()`
        3. call to the decorated function, could use `self.stub` as the stubbed loader
        4. call `hard_reset()`
        5. create the `self.forward_io` thread again.
        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.proc.close()
            self.proc.open()

            settings = self.proc.get_settings()

            try:
                with DuplicateStdout(self.pexpect_proc):
                    self.esp.connect('hard_reset')
                    self.stub = self.esp.run_stub()
                    ret = func(self, *args, **kwargs)
                    self.stub.hard_reset()
            finally:
                self.proc.apply_settings(settings)
                self.create_forward_io_thread(self.pexpect_proc)

            return ret

        return wrapper

    @use_esptool
    def _start(self):
        pass
