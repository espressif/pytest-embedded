import copy
from typing import Optional

import pexpect
import serial as pyserial
from pytest_embedded.log import DuplicateStdout, DuplicateStdoutMixin
from pytest_embedded.utils import to_str


class Serial(DuplicateStdoutMixin):
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

    def __init__(self, port: str, pexpect_proc: Optional[pexpect.spawn] = None, **kwargs):
        """
        Args:
            port: port
            pexpect_proc: `PexpectProcess` instance
        """
        super().__init__()

        if port is None:
            raise ValueError('please specify port')
        else:
            self.port = port

        self.pexpect_proc = pexpect_proc
        self.port_config = copy.deepcopy(self.DEFAULT_PORT_CONFIG)
        self.port_config.update(**kwargs)

        self.proc = pyserial.serial_for_url(self.port, **self.port_config)

        self.proc_close_methods.append(self.proc.close)

        self._start()

    def _start(self):
        pass

    def _forward_io(
        self, pexpect_proc: Optional[pexpect.spawn] = None, source: Optional[str] = None, breaker=b'\n'
    ) -> None:
        with DuplicateStdout(pexpect_proc, source):
            while True:
                line = b''
                sess_output = self.proc.read()  # a single char
                while sess_output and sess_output != breaker:
                    line += sess_output
                    sess_output = self.proc.read()
                line += sess_output
                line = to_str(line)
                print(line)
