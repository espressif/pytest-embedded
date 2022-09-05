import contextlib
import copy
import logging
from typing import Dict, Union

import serial as pyserial
from pytest_embedded.log import DuplicateStdoutMixin, PexpectProcess


class Serial(DuplicateStdoutMixin):
    """
    Custom serial class

    Attributes:
        port_config (dict[str, Any]): port configs
        proc (serial.Serial): process created by `serial.serial_for_url()`
    """

    DEFAULT_BAUDRATE = 115200

    DEFAULT_PORT_CONFIG = {
        'baudrate': DEFAULT_BAUDRATE,
        'bytesize': pyserial.EIGHTBITS,
        'parity': pyserial.PARITY_NONE,
        'stopbits': pyserial.STOPBITS_ONE,
        'timeout': 0.05,  # read timeout
        'xonxoff': False,
        'rtscts': False,
    }

    occupied_ports: Dict[str, None] = dict()

    def __init__(
        self,
        pexpect_proc: PexpectProcess,
        port: Union[str, pyserial.Serial],
        baud: int = DEFAULT_BAUDRATE,
        **kwargs,
    ):
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            port: port string or pyserial Serial instance
        """
        super().__init__()

        if port is None:
            raise ValueError('Please specify port')

        if isinstance(port, str):
            self.port = port
            self.port_config = copy.deepcopy(self.DEFAULT_PORT_CONFIG)
            self.port_config['baudrate'] = baud
            self.port_config.update(**kwargs)
            self.proc = pyserial.serial_for_url(self.port, **self.port_config)
        else:  # pyserial instance
            self.proc = port
            self.proc.timeout = self.DEFAULT_PORT_CONFIG['timeout']  # set read timeout
            self.port = self.proc.port

        self.pexpect_proc = pexpect_proc
        self.baud = baud

        self._post_init()

        self._start()

        self._finalize_init()

    def _post_init(self):
        pass

    def _start(self):
        pass

    def _finalize_init(self):
        self.occupied_ports[self.port] = None
        logging.debug(f'occupied {self.port}')

    def _forward_io(self, pexpect_logfile: str) -> None:
        while self.proc.is_open:
            try:
                s = self.proc.read_all()
                PexpectProcess.write_to_file(pexpect_logfile, s)
            except:  # noqa daemon thread may run at any case
                break

    def close(self):
        self.proc.close()
        self._forward_io_proc.terminate()

    @contextlib.contextmanager
    def disable_redirect_thread(self):
        killed = False
        if self._forward_io_proc and self._forward_io_proc.is_alive():
            self._forward_io_proc.terminate()
            killed = True

        yield killed

        if killed:
            self.create_forward_io_proc(self.pexpect_proc.filepath)
