import copy
import logging
import multiprocessing
import time
from typing import List

import serial as pyserial
from pytest_embedded.utils import InternalError


class Serial(multiprocessing.Process):
    """
    Custom serial class

    Attributes:
        port (str): port address
        baud (int): baud rate
        port_config (dict[str, Any]): port configs
        proc (pyserial.Serial): process created by `serial.serial_for_url()`

    Warnings:
        - the real `pyserial` object must be created inside `self._forward_io`,
          The `pyserial` object can't be pickled when using multiprocessing.Process
        - make sure this `Serial` __init__ run the last in MRO
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

    def __init__(
        self,
        msg_queue: multiprocessing.Queue,
        occupied_ports: multiprocessing.Queue,
        port: str,
        baud: int = DEFAULT_BAUDRATE,
        **kwargs,
    ):
        self._q = msg_queue
        self._q_used_ports = occupied_ports

        self.port = port
        self.baud = baud

        if port is None:
            raise ValueError('Please specify port')

        if port in self.occupied_ports:
            raise ValueError('port {} is already being used. Occupied ports: {}', port, self.occupied_ports)

        if not isinstance(port, str):
            raise ValueError('`port` must be str, the real `pyserial` object must be created inside `self._forward_io`')

        self.port_config = copy.deepcopy(self.DEFAULT_PORT_CONFIG)
        self.port_config['baudrate'] = baud
        self.port_config.update(**kwargs)

        self.proc: pyserial.Serial = None  # type: ignore

        super().__init__(target=self._forward_io, daemon=True)  # killed by the main process
        self._post_init()
        self._start()

        self.start()  # start self process

    @property
    def occupied_ports(self) -> List[str]:
        """
        The occupied ports queue should be a dict that hold all the targets
        """
        ports = self._q_used_ports.get()
        self._q_used_ports.put(ports)  # insert back immediately
        return list(ports)

    def occupy_port(self) -> None:
        ports = self._q_used_ports.get()
        ports[self.port] = None
        self._q_used_ports.put(ports)
        logging.debug(f'occupied {self.port}')

    def release_port(self) -> None:
        ports = self._q_used_ports.get()
        try:
            ports.pop(self.port)
        except KeyError:
            raise InternalError(f'port {self.port} not occupied. occupied ports: {ports}')
        self._q_used_ports.put(ports)
        logging.debug(f'released {self.port}')

    def _post_init(self):
        self.occupy_port()

    def _start(self):
        pass

    def _forward_io(self) -> None:
        self.proc = pyserial.serial_for_url(self.port, **self.port_config)
        while self.proc.is_open:
            try:
                s = self.proc.read_all()
                self._q.put(s)
                time.sleep(0.1)
            except Exception as e:
                logging.error(e)

    def terminate(self, **kwargs):
        self.proc.close()
        self.release_port()
        super().terminate(**kwargs)
