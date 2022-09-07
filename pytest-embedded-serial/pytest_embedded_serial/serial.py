import copy
import logging
import multiprocessing
import time
from typing import Dict

import serial as pyserial


class Serial(multiprocessing.Process):
    """
    Custom serial class

    Attributes:
        port (str): port address
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
        msg_queue: multiprocessing.Queue,
        port: str,
        baud: int = DEFAULT_BAUDRATE,
        **kwargs,
    ):
        """
        Args:
            msg_queue: message queue
            port: port string
            baud: baud rate

        Warnings:
            the real `pyserial` object must be created inside `self._forward_io`.
            The `pyserial` object can't be pickled when using multiprocessing.Process
        """
        self.q = msg_queue
        self.port = port
        self.baud = baud

        if port is None:
            raise ValueError('Please specify port')

        if not isinstance(port, str):
            raise ValueError('`port` must be str, the real `pyserial` object must be created inside `self._forward_io`')

        self.port_config = copy.deepcopy(self.DEFAULT_PORT_CONFIG)
        self.port_config['baudrate'] = baud
        self.port_config.update(**kwargs)

        self.proc: pyserial.Serial = None  # type: ignore

        super().__init__(target=self._forward_io, daemon=True)  # killed by the main process
        self.start()

    def _post_init(self):
        pass

    def _start(self):
        pass

    def _finalize_init(self):
        self.occupied_ports[self.port] = None
        logging.debug(f'occupied {self.port}')

    def _forward_io(self) -> None:
        self.proc = pyserial.serial_for_url(self.port, **self.port_config)

        self._start()

        self._post_init()

        self._finalize_init()

        while self.proc.is_open:
            s = self.proc.read_all()
            self.q.put(s)
            time.sleep(0.1)

    def close(self):
        self.proc.close()
        super().close()
