import copy
import multiprocessing
from typing import Union

import serial as pyserial
from pytest_embedded.log import DuplicateStdout, PexpectProcess
from pytest_embedded.utils import to_str


class Serial:
    """
    Custom serial class

    Attributes:
        port_config (dict[str, Any]): port configs
        proc (serial.Serial): process created by `serial.serial_for_url()`
    """

    DEFAULT_PORT_CONFIG = {
        'baudrate': 115200,
        'bytesize': pyserial.EIGHTBITS,
        'parity': pyserial.PARITY_NONE,
        'stopbits': pyserial.STOPBITS_ONE,
        'timeout': 0.05,
        'xonxoff': False,
        'rtscts': False,
    }

    def __init__(self, pexpect_proc: PexpectProcess, port: Union[str, pyserial.Serial], **kwargs):
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            port: port string or pyserial Serial instance
        """
        super().__init__()

        if port is None:
            raise ValueError('please specify port')

        if isinstance(port, str):
            self.port = port
            self.port_config = copy.deepcopy(self.DEFAULT_PORT_CONFIG)
            self.port_config.update(**kwargs)
            self.proc = pyserial.serial_for_url(self.port, **self.port_config)
        elif isinstance(port, pyserial.Serial):  # pyserial instance
            self.proc = port
            self.proc.timeout = self.DEFAULT_PORT_CONFIG['timeout']  # set read timeout
            self.port = self.proc.port
        else:
            raise ValueError('port should be a string or a pyserial.Serial instance')

        self.pexpect_proc = pexpect_proc

        # pyserial instance doesn't support redirect to other file descriptor, use a redirect process instead
        self.redirect_proc = multiprocessing.Process(target=self._forward_io)

        self._start()

    def _start(self):
        pass

    def _forward_io(self) -> None:
        with DuplicateStdout(self.pexpect_proc, 'serial'):
            while self.proc.is_open:
                print(to_str(self.proc.readall()))
