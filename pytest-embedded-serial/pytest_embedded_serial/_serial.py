import io
import multiprocessing
import os
import sys
import tempfile
from typing import Optional, Tuple

import esptool as esptool
import serial
from pytest_embedded.app import App
from pytest_embedded.dut import DUT
from serial.tools.list_ports_posix import comports


class SerialDUT(DUT):
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

        self.target = getattr(self, 'target', 'auto')
        self.target, self.port = detect_target_port(self.target, port)

        self.port_config = self.DEFAULT_PORT_CONFIG

        # forward_io_proc would get output from ``open_port_session``, do some pre-process jobs and then forward the
        # the output to the ``pexpect_proc``, which only accept type str as input
        self.port_session = self.open_port_session()
        self.forward_io_proc = self.open_forward_io_process()
        self.forward_io_proc.start()

        self._sessions_close_methods.extend([
            self.forward_io_proc.terminate,
            self.port_session.close,
        ])

    def preprocess(self, byte_str) -> str:
        if isinstance(byte_str, bytes):
            return byte_str.decode('ascii')
        return byte_str

    def open_forward_io_process(self) -> multiprocessing.Process:
        proc = multiprocessing.Process(target=self.forward_io)
        return proc

    def forward_io(self, breaker: bytes = b'\n'):
        while True:
            line = b''
            sess_output = self.port_session.read()  # a single char
            while sess_output and sess_output != breaker:
                line += sess_output
                sess_output = self.port_session.read()
            line += sess_output
            line = self.preprocess(line)
            self.pexpect_proc.write(line)

    def open_port_session(self) -> io.BytesIO:
        serial_port = SerialPort(self.port, **self.port_config)
        serial_port.flash(self.app)
        serial_port.close()

        return serial.serial_for_url(self.port, **self.port_config)


class SerialPort(serial.Serial):
    def __init__(self, *args, **kwargs):
        super(SerialPort, self).__init__(*args, **kwargs)

    def flash(self, app: App, erase_nvs=True):
        last_error = None
        for baud_rate in [921600, 115200]:
            try:
                self.try_flash(app, erase_nvs, baud_rate)
                break
            except RuntimeError as e:
                last_error = e
        else:
            raise last_error

    def try_flash(self, app: App, erase_nvs=True, baud_rate=115200):
        rom_inst = esptool.ESPLoader.detect_chip(self)
        settings = self.get_settings()

        rom_inst.connect('hard_reset')
        esp = rom_inst.run_stub()

        flash_files = app.flash_files
        encrypt_files = app.encrypt_files
        encrypt = app.flash_settings.get('encrypt', False)
        if encrypt:
            flash_files = encrypt_files
            encrypt_files = []
        else:
            flash_files = [entry for entry in flash_files if entry not in encrypt_files]

        flash_files = [(offs, open(path, 'rb')) for (offs, path) in flash_files]
        encrypt_files = [(offs, open(path, 'rb')) for (offs, path) in encrypt_files]

        # fake flasher args object, this is a hack until
        # esptool Python API is improved
        class FlashArgs(object):
            def __init__(self, attributes):
                for key, value in attributes.items():
                    self.__setattr__(key, value)

        # write_flash expects the parameter encrypt_files to be None and not
        # an empty list, so perform the check here
        flash_args = FlashArgs({
            'flash_size': app.flash_settings['flash_size'],
            'flash_mode': app.flash_settings['flash_mode'],
            'flash_freq': app.flash_settings['flash_freq'],
            'addr_filename': flash_files,
            'encrypt_files': encrypt_files or None,
            'no_stub': False,
            'compress': True,
            'verify': False,
            'encrypt': encrypt,
            'ignore_flash_encryption_efuse_setting': False,
            'erase_all': False,
        })

        nvs_file = None
        if erase_nvs:
            address = app.partition_table['nvs']['offset']
            size = app.partition_table['nvs']['size']
            nvs_file = tempfile.NamedTemporaryFile(delete=False)
            nvs_file.write(b'\xff' * size)
            if not isinstance(address, int):
                address = int(address, 0)

            if encrypt:
                encrypt_files.append((address, open(nvs_file.name, 'rb')))
            else:
                flash_files.append((address, open(nvs_file.name, 'rb')))

        try:
            esp.change_baud(baud_rate)
            esptool.detect_flash_size(esp, flash_args)
            esptool.write_flash(esp, flash_args)
        except Exception:  # noqa
            raise
        else:
            esp.hard_reset()
        finally:
            if nvs_file:
                nvs_file.close()
                os.remove(nvs_file.name)
            for (_, f) in flash_files:
                f.close()
            for (_, f) in encrypt_files:
                f.close()
            self.apply_settings(settings)


def _list_available_ports():
    def _sort_usb_ports(_ports):
        # we only use usb ports
        usb_ports = []
        for port in _ports:
            if 'usb' in port.lower():
                usb_ports.append(port)
        return usb_ports

    ports = _sort_usb_ports([x.device for x in comports()])
    espport = os.getenv('ESPPORT')
    if not espport:
        return ports

    # If $ESPPORT is a valid port, make it appear first in the list
    if espport in ports:
        ports.remove(espport)
        return [espport] + ports

    # On macOS, user may set ESPPORT to /dev/tty.xxx while
    # pySerial lists only the corresponding /dev/cu.xxx port
    if sys.platform == 'darwin' and 'tty.' in espport:
        espport = espport.replace('tty.', 'cu.')
        if espport in ports:
            ports.remove(espport)
            return [espport] + ports
    return ports


def _rom_target_name(rom: esptool.ESPLoader) -> str:
    return rom.__class__.CHIP_NAME.lower().replace('-', '')


def _judge_by_target(ports: list[str], target: str = 'auto') -> Tuple[str, str]:
    for port in ports:
        inst = None
        try:
            inst = esptool.ESPLoader.detect_chip(port)
            inst_target = _rom_target_name(inst)
            if target == 'auto' or inst_target == target:
                return inst_target, port
        except Exception:  # noqa
            continue
        finally:
            if inst is not None:
                inst._port.close()
    raise ValueError(f'Target "{target}" port not found')


def _judge_by_port(port: str) -> Tuple[str, str]:
    inst = None
    try:
        inst = esptool.ESPLoader.detect_chip(port)
    except Exception:  # noqa
        raise
    else:
        return _rom_target_name(inst), port
    finally:
        if inst is not None:
            inst._port.close()


def detect_target_port(target=None, port=None) -> Tuple[str, str]:
    available_ports = _list_available_ports()

    if target:
        if port:
            return target, port
        else:
            return _judge_by_target(available_ports, target)
    elif port:
        if port not in available_ports:
            raise ValueError(f'Port "{port}" unreachable')
        return _judge_by_port(port)
    else:  # pick the first available port then...
        return _judge_by_target(available_ports, 'auto')
