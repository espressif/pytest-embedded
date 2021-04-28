from typing import IO

import serial

DEFAULT_CONFIG = {
    'baudrate': 115200,
    'bytesize': serial.EIGHTBITS,
    'parity': serial.PARITY_NONE,
    'stopbits': serial.STOPBITS_ONE,
    'timeout': 0.05,
    'xonxoff': False,
    'rtscts': False,
}

# could be changed by pytest cli options
DEFAULT_PORT = '/dev/ttyUSB1'


def get_raw_output_io(self) -> IO:
    port = getattr(self, 'port', DEFAULT_PORT)
    config = getattr(self, 'raw_output_config', DEFAULT_CONFIG)
    return serial.serial_for_url(port, **config)
