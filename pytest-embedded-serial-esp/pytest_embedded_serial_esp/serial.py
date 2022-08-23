import functools
import logging
from enum import Enum
from typing import Dict, Optional

import esptool
from pytest_embedded.log import DuplicateStdout, PexpectProcess
from pytest_embedded_serial.dut import Serial


class EsptoolVersion(Enum):
    V3 = 3
    V4 = 4


class EspSerial(Serial):
    """
    Serial class for ports connected to espressif products

    Attributes:
        esp: esptool.ESPLoader, will auto upload stub.
        stub: esptool.ESPStubLoader, stubbed loader.
    """

    ESPTOOL_DEFAULT_BAUDRATE = 921600

    try:
        # esptool>=4.0
        from esptool import __version__
        from esptool.loader import ESPLoader
        from esptool.targets import CHIP_LIST

        ESPTOOL_VERSION = EsptoolVersion.V4
        ESPTOOL_CHIPS = CHIP_LIST
        _ESPTOOL_RAW_VERSION = __version__
    except (AttributeError, ModuleNotFoundError):
        # esptool<4.0
        from esptool import SUPPORTED_CHIPS, ESPLoader, __version__

        ESPTOOL_VERSION = EsptoolVersion.V3
        ESPTOOL_CHIPS = SUPPORTED_CHIPS
        _ESPTOOL_RAW_VERSION = __version__

    def __init__(
        self,
        pexpect_proc: PexpectProcess,
        target: Optional[str] = None,
        beta_target: Optional[str] = None,
        port: Optional[str] = None,
        baud: int = Serial.DEFAULT_BAUDRATE,
        esptool_baud: int = ESPTOOL_DEFAULT_BAUDRATE,
        skip_autoflash: bool = False,
        erase_all: bool = False,
        port_target_cache: Dict[str, str] = None,
        **kwargs,
    ) -> None:
        self._port_target_cache: Dict[str, str] = port_target_cache if port_target_cache is not None else {}

        esptool_target = beta_target or target
        if port is None:
            available_ports = esptool.get_port_list()
            ports = list(set(available_ports) - set(self.occupied_ports.keys()))

            # sort to make /dev/ttyS* ports before /dev/ttyUSB* ports
            # esptool will reverse the list
            ports.sort()

            # prioritize the cache recorded target port
            if esptool_target:
                for _port, _target in self._port_target_cache.items():
                    if _target == esptool_target and _port in ports:
                        ports.sort(key=lambda x: x == _port)
                        logging.debug('hit port-target cache: %s - %s', _port, _target)

            logging.debug(f'Detecting ports from {", ".join(ports)}')
        else:
            ports = [port]

        with DuplicateStdout(pexpect_proc):
            # normal loader
            if esptool_target not in (['auto'] + self.ESPTOOL_CHIPS):
                raise ValueError(
                    f'esptool version {self._ESPTOOL_RAW_VERSION} not support target {esptool_target}\n'
                    f'Supported targets: {self.ESPTOOL_CHIPS}'
                )

            self.esp: esptool.ESPLoader = esptool.get_default_connected_device(
                ports,
                port=port,
                connect_attempts=3,
                initial_baud=baud,
                chip=esptool_target,
            )
            if not self.esp:
                raise ValueError('Couldn\'t auto detect chip. Please manually specify with "--port"')

            # stub loader has more functionalities, need to run after calling `run_stub()`
            self.stub: esptool.ESPLoader = self.esp.run_stub()

        target = self.esp.CHIP_NAME.lower().replace('-', '')
        logging.info(f'Target: %s, Port: %s', target, self.esp.serial_port)

        self.target = target

        self.skip_autoflash = skip_autoflash
        self.erase_all = erase_all
        self.esptool_baud = esptool_baud
        super().__init__(pexpect_proc, port=self.esp._port, baud=baud, **kwargs)

    def _post_init(self):
        logging.debug('set port-target cache: %s - %s', self.port, self.target)
        self._port_target_cache[self.port] = self.target
        super()._post_init()

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
            with self.disable_redirect_thread() as killed:
                settings = self.proc.get_settings()
                try:
                    with DuplicateStdout(self.pexpect_proc):
                        if killed:
                            self.esp.connect('hard_reset')
                            self.stub = self.esp.run_stub()
                        ret = func(self, *args, **kwargs)
                        self.stub.hard_reset()
                finally:
                    self.proc.apply_settings(settings)

            return ret

        return wrapper

    def _start(self):
        self.hard_reset()

    @use_esptool
    def hard_reset(self):
        """Hard reset your espressif device"""
        pass
