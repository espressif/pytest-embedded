import contextlib
import copy
import logging
import multiprocessing
import queue
import threading
import time
from typing import Any, ClassVar

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
        proc (pyserial.Serial): process created by `serial.serial_for_url()`

    Warning:
        - make sure this `Serial.__init__()` run the last in MRO, it would create and start the redirect serial process
    """

    DEFAULT_BAUDRATE = 115200

    DEFAULT_PORT_CONFIG: ClassVar[dict[str, Any]] = {
        'baudrate': DEFAULT_BAUDRATE,
        'bytesize': pyserial.EIGHTBITS,
        'parity': pyserial.PARITY_NONE,
        'stopbits': pyserial.STOPBITS_ONE,
        'timeout': 0.05,  # read timeout
        'xonxoff': False,
        'rtscts': False,
    }

    occupied_ports: ClassVar[dict[str, None]] = dict()

    def __init__(
        self,
        msg_queue: MessageQueue,
        port: str | None = None,
        port_location: str | None = None,
        baud: int = DEFAULT_BAUDRATE,
        meta: Meta | None = None,
        stop_after_init: bool = False,
        ports_to_occupy: list[str] = (),
        **kwargs,
    ):
        self._q = msg_queue
        self._meta = meta
        self._redirect_thread: _SerialRedirectThread = None  # type: ignore

        self.baud = baud
        self.ports_to_occupy = ports_to_occupy if ports_to_occupy else []

        if isinstance(port, pyserial.SerialBase):
            self.proc = port
            self.proc.timeout = self.DEFAULT_PORT_CONFIG['timeout']  # set read timeout
            self.port = self.proc.port
        else:
            # Need to detect or create instance
            if port_location:
                for _port in list_ports.comports():
                    if _port.device in self.occupied_ports:
                        continue
                    if _port.location == port_location:
                        if port and _port.device != port:
                            raise ValueError(
                                f'The specified location {port_location} binds with port {_port.device}, not {port}'
                            )

                        self.port = _port.device
                        break
                else:
                    raise ValueError(f'The specified location {port_location} cannot be found.')
            elif port:
                self.port = port
            else:
                raise ValueError('Please specify port or provide the port location')

            self.port = port
            port_config = copy.deepcopy(self.DEFAULT_PORT_CONFIG)
            port_config['baudrate'] = baud
            port_config.update(**kwargs)
            self.proc = pyserial.serial_for_url(self.port, **port_config)

        self.ports_to_occupy.append(self.port)
        self._post_init()
        try:
            self._start()
        except Exception as e:
            self.close()
            raise e
        self._finalize_init()
        if not stop_after_init:
            self.start_redirect_thread()
        else:
            self.close()

    def start_redirect_thread(self) -> None:
        if self._redirect_thread and self._redirect_thread.is_alive():
            return

        # Here the reason why we're still using thread is,
        # the `pyserial` object can't be pickled when using multiprocessing.Process
        self._redirect_thread = _SerialRedirectThread(self._q, self.proc)
        self._redirect_thread.start()

    def stop_redirect_thread(self) -> bool:
        killed = False
        if self._redirect_thread and self._redirect_thread.is_alive():
            self._redirect_thread.terminate()
            killed = True

        return killed

    def _post_init(self):
        pass

    def _start(self):
        pass

    def _finalize_init(self):
        occupied_ports = []
        for port in self.ports_to_occupy:
            if port not in self.occupied_ports:
                self.occupied_ports[port] = None
                occupied_ports.append(port)
                logging.debug(f'occupied {port}')
            else:
                logging.warning(f'port {port} is already occupied')
        self.ports_to_occupy = occupied_ports

    def close(self):
        self.stop_redirect_thread()
        self.proc.close()
        for port in self.ports_to_occupy:
            self.occupied_ports.pop(port, None)
            logging.debug(f'released {port}')

    @contextlib.contextmanager
    def disable_redirect_thread(self) -> bool:
        """
        kill the redirect thread, and start a new one after got yield back

        Yields:
            True if redirect serial thread has been terminated
        """
        killed = self.stop_redirect_thread()

        yield killed

        if killed:
            self.start_redirect_thread()


class _SerialRedirectThread(threading.Thread):
    """
    Redirect serial thread
    """

    def __init__(self, msg_queue: MessageQueue, s: pyserial.Serial):
        self._q = msg_queue
        self._event_q = multiprocessing.Queue()
        self._s = s

        self._block_reading = False

        super().__init__(target=self._event_loop, daemon=True)  # killed by the main process

    def _event_loop(self):
        """
        Since pyserial.Serial instance can't be serialized, we pass the `_serial` as an reference of the object
        defined in _forward_io. The pyserial.Serial methods are mocked to send an event to the queue, and the real
        method is running here.
        """
        while True:
            try:
                _e = self._event_q.get_nowait()
            except queue.Empty:
                _e = 'read'
            except OSError:
                return

            if _e == 'read':
                if self._block_reading:
                    continue

                try:
                    s = self._s.read_all()
                    self._q.put(s)
                except OSError:
                    return
                except Exception as e:
                    logging.warning(
                        'unknown error: %s.\nRecommend to close the serial process by `dut.serial.close()`', str(e)
                    )
                    return

            elif _e == 'stop':
                self._block_reading = True
            elif _e == 'start':
                self._block_reading = False
            elif _e == 'end':
                return

            time.sleep(0.05)  # set interval

    def stop_reading(self):
        self._event_q.put('stop')

    def start_reading(self):
        self._event_q.put('start')

    def terminate(self):
        self._event_q.put('end')
        self.join()
