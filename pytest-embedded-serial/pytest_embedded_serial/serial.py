import contextlib
import copy
import inspect
import logging
import multiprocessing
import queue
from typing import Dict, Optional

import serial as pyserial
from pytest_embedded.log import MessageQueue
from pytest_embedded.utils import Meta
from serial.tools import list_ports


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
        msg_queue: MessageQueue,
        port: str = None,
        port_location: str = None,
        baud: int = DEFAULT_BAUDRATE,
        meta: Optional[Meta] = None,
        **kwargs,
    ):
        self._q = msg_queue
        self._meta = meta

        self.port = port
        self.baud = baud

        if port is None and not port_location:
            raise ValueError('Please specify port or provide the port location')
        if port_location:
            for port in list_ports.comports():
                if port.device in self.occupied_ports:
                    continue
                if port.location == port_location:
                    if self.port and port.device != self.port:
                        raise ValueError(
                            f'The specified location {port_location} binds with port {port.device}, not {self.port}'
                        )

                    self.port = port.device
                    break
            else:
                raise ValueError(f'The specified location {port_location} cannot be found.')

        if not isinstance(self.port, str):
            raise ValueError('`port` must be str, the real `pyserial` object must be created inside `self._forward_io`')

        self.port_config = copy.deepcopy(self.DEFAULT_PORT_CONFIG)
        self.port_config['baudrate'] = baud
        self.port_config.update(**kwargs)

        self.proc: _SerialRedirectProcess = None  # type: ignore

        self._post_init()
        self._start()
        self._finalize_init()

        self.start_redirect_process()

    def start_redirect_process(self):
        if self.proc and self.proc.is_alive():
            return

        self.proc = _SerialRedirectProcess(self._q, self.port, self.port_config)
        self.proc.start()

    def stop_redirect_process(self) -> bool:
        killed = False
        if self.proc and self.proc.is_alive():
            while self.proc.is_alive():
                self.proc.terminate()
            killed = True

        return killed

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
        killed = self.stop_redirect_process()

        yield killed

        if killed:
            self.start_redirect_process()


class _SerialRedirectProcess(multiprocessing.Process):
    """
    Redirect serial process. All pyserial.Serial methods was also runnable within this class.

    Warning:
        All attributes under this class or its sub-classes must be serializable.
    """

    def __init__(self, msg_queue, port, port_config):
        self._q = msg_queue
        self._event_q = multiprocessing.Queue()

        self.port = port
        self.port_config = port_config

        super().__init__(target=self._forward_io, daemon=True)  # killed by the main process

    def _forward_io(self) -> None:
        _serial = pyserial.serial_for_url(self.port, **self.port_config)

        while _serial.is_open:
            try:
                self._event_loop(_serial)
            except Exception as e:
                logging.error(e)

    def _event_loop(self, _serial: pyserial.Serial):
        """
        Since pyserial.Serial instance can't be serialized, we pass the `_serial` as an reference of the object
        defined in _forward_io. The pyserial.Serial methods are mocked to send an event to the queue, and the real
        method is running here.
        """
        try:
            _e, _args, _kwargs = self._event_q.get_nowait()
            logging.debug('running method %s with args %s and kwargs %s', _e, _args, _kwargs)
        except queue.Empty:
            _e, _args, _kwargs = 'read', [], {}

        if _e == 'read':
            try:
                s = _serial.read_all()
                self._q.put(s)
            except Exception as e:
                logging.error(e)
        else:
            try:
                getattr(_serial, _e)(*_args, **_kwargs)
            except Exception as e:
                logging.error(e)


def _mock_pyserial_method(name):
    def real_func(self, *args, **kwargs):
        logging.debug('Mocking method "%s" with args %s kwargs %s', name, args, kwargs)
        self._event_q.put((name, args, kwargs))

    return real_func


# mock pyserial Serial methods into this class
_pyserial_func = inspect.getmembers(pyserial.Serial, predicate=inspect.isfunction)
for _f_name, _ in _pyserial_func:
    if not _f_name.startswith('__'):  # not magic functions
        setattr(_SerialRedirectProcess, _f_name, _mock_pyserial_method(_f_name))
