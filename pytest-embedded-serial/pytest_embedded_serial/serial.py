import contextlib
import copy
import logging
import multiprocessing
import time
from typing import Dict

import serial as pyserial


class Serial:
    """
    Custom serial class

    Attributes:
        port (str): port address
        baud (int): baud rate
        port_config (dict[str, Any]): port configs
        proc (pyserial.Serial): process created by `serial.serial_for_url()`

    Warning:
        - the real `pyserial` object must be created inside `self._forward_io`,
          The `pyserial` object can't be pickled when using multiprocessing.Process
        - make sure this `Serial` __init__ run the last in MRO, it would create and start the redirect serial process
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
        self._q = msg_queue
        self.port = port
        self.baud = baud

        if port is None:
            raise ValueError('Please specify port')

        if not isinstance(port, str):
            raise ValueError('`port` must be str, the real `pyserial` object must be created inside `self._forward_io`')

        self.port_config = copy.deepcopy(self.DEFAULT_PORT_CONFIG)
        self.port_config['baudrate'] = baud
        self.port_config.update(**kwargs)

        self.proc: _SerialRedirectProcess = None  # type: ignore

        self._post_init()
        self._start()
        self._finalize_init()

        self.start_redirect_serial_process()

    def start_redirect_serial_process(self):
        if self.proc and self.proc.is_alive():
            return

        self.proc = _SerialRedirectProcess(self._q, self.port, self.port_config)
        self.proc.start()

    def _post_init(self):
        pass

    def _start(self):
        pass

    def _finalize_init(self):
        self.occupied_ports[self.port] = None
        logging.debug(f'occupied {self.port}')

    def close(self):
        self.proc.terminate()
        self.occupied_ports.pop(self.port, None)
        logging.debug(f'released {self.port}')

    @contextlib.contextmanager
    def disable_redirect_serial(self) -> bool:
        """
        Close the redirect serial process, and start the redirect process again after yield back

        Yields:
            True if redirect serial process is been killed
        """
        killed = False
        if self.proc and self.proc.is_alive():
            self.proc.terminate()
            # wait the serial port is closed by the `Process.terminate()`
            # mostly for windows compatibility
            time.sleep(1)
            killed = True

        yield killed

        if killed:
            self.start_redirect_serial_process()


class _SerialRedirectProcess(multiprocessing.Process):
    """
    Redirect serial process

    Warning:
        All attributes under this class or its sub-classes must be serializable.
    """

    def __init__(self, msg_queue, port, port_config):
        self._q = msg_queue
        self.port = port
        self.port_config = port_config

        super().__init__(target=self._forward_io, daemon=True)  # killed by the main process

    def _forward_io(self) -> None:
        _serial = pyserial.serial_for_url(self.port, **self.port_config)

        while _serial.is_open:
            try:
                s = _serial.read_all()
                self._q.put(s)
            except Exception as e:
                logging.error(e)
