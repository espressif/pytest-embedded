import multiprocessing
from typing import Optional

import serial
from pytest_embedded.app import App
from pytest_embedded.dut import Dut
from pytest_embedded.log import to_str


class SerialDut(Dut):
    """
    Dut class for serial ports

    :ivar: port: serial port string
    :ivar: port_inst: :class:`pyserial.Serial` instance
    :ivar: forward_io_proc: A process which forward the serial output to :attr:`pexpect_proc` stdin
    """

    DEFAULT_PORT_CONFIG = {
        'baudrate': 115200,
        'bytesize': serial.EIGHTBITS,
        'parity': serial.PARITY_NONE,
        'stopbits': serial.STOPBITS_ONE,
        'timeout': 0.05,
        'xonxoff': False,
        'rtscts': False,
    }

    def __init__(self, app: Optional[App] = None, port: Optional[str] = None, *args, **kwargs) -> None:
        super().__init__(app, *args, **kwargs)

        if port is None:
            raise ValueError('please specify port')
        else:
            self.port = port

        self.port_config = self.DEFAULT_PORT_CONFIG
        self.port_inst = self._open_port_session()
        self._start()

        # forward_io_proc would get output from ``open_port_session``, do some pre-process jobs and then forward the
        # the output to the ``pexpect_proc``, which only accept type str as input
        self.forward_io_proc = self._open_forward_io_process()
        self.forward_io_proc.start()

        self._sessions_close_methods.extend(
            [
                self.forward_io_proc.terminate,
                self.port_inst.close,
            ]
        )

    def _start(self):
        pass

    def _open_port_session(self) -> serial.Serial:
        return serial.serial_for_url(self.port, **self.port_config)

    def _open_forward_io_process(self) -> multiprocessing.Process:
        proc = multiprocessing.Process(target=self._forward_io)
        return proc

    @Dut.redirect_stdout('serial')
    def _forward_io(self, breaker: bytes = b'\n'):
        while True:
            line = b''
            sess_output = self.port_inst.read()  # a single char
            while sess_output and sess_output != breaker:
                line += sess_output
                sess_output = self.port_inst.read()
            line += sess_output
            line = to_str(line)
            print(line)
