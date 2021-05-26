import functools
import logging
import os
import sys
from typing import List, Optional, Tuple

import esptool
from pytest_embedded.app import App
from pytest_embedded.dut import Dut
from pytest_embedded_serial.dut import SerialDut
from serial.tools.list_ports_posix import comports


class EspSerialDut(SerialDut):
    """
    Dut class for espressif serial port

    :ivar: target: target chip type
    :ivar: port: serial port string
    """

    def __init__(self, app: Optional[App] = None, port: Optional[str] = None, *args, **kwargs) -> None:
        self.target = getattr(app, 'target', 'auto')
        self.target, port = self.detect_target_port(port)
        logging.info(f'Target: {self.target}, Port: {port}')

        # put at last to make sure the forward_io_proc is forwarding output after the hard reset
        super().__init__(app, port, *args, **kwargs)

    def _uses_esptool(func):
        """
        Provided functionalities:
        - run hard_reset before real function run
        - reset the port settings after real function run
        - call ``run_stub()`` and pass the ESPStubLoader instance
        """

        @functools.wraps(func)
        def handler(self, *args, **kwargs):
            settings = self.port_inst.get_settings()

            if getattr(self, 'rom_inst', None) is None:
                self.rom_inst = esptool.ESPLoader.detect_chip(self.port_inst)

            try:
                self.rom_inst.connect('hard_reset')
                stub_inst = self.rom_inst.run_stub()

                ret = func(self, stub_inst, *args, **kwargs)
                # do hard reset after use esptool
                stub_inst.hard_reset()
            finally:
                self.port_inst.apply_settings(settings)
            return ret

        return handler

    @_uses_esptool
    def hard_reset(self, stub_inst: esptool.ESPLoader):
        """
        Hard reset via esptool
        """
        pass

    def _start(self) -> None:
        self.hard_reset()

    @Dut.redirect_stdout('detecting port')
    def detect_target_port(self, port: Optional[str] = None) -> Tuple[str, str]:
        """
        Returns the target chip type and port. Will do auto-detection if argument ``target`` or ``port`` or both of them
        are missing.

        :param port: serial port
        :return: specific chip type and port
        """
        available_ports = _list_available_ports()

        if self.target:
            if port:
                return self.target, port
            else:
                return _judge_by_target(available_ports, self.target)
        elif port:
            if port not in available_ports:
                raise ValueError(f'Port "{port}" unreachable')
            return _judge_by_port(port)
        else:  # pick the first available port then...
            return _judge_by_target(available_ports, 'auto')


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


def _judge_by_target(ports: List[str], target: str = 'auto') -> Tuple[str, str]:
    for port in ports:
        rom_inst = None
        try:
            rom_inst = esptool.ESPLoader.detect_chip(port)
            inst_target = _rom_target_name(rom_inst)
            if target == 'auto' or inst_target == target:
                return inst_target, port
        except Exception:  # noqa
            continue
        finally:
            if rom_inst is not None:
                rom_inst._port.close()
    raise ValueError(f'Target "{target}" port not found')


def _judge_by_port(port: str) -> Tuple[str, str]:
    rom_inst = None
    try:
        rom_inst = esptool.ESPLoader.detect_chip(port)
    except Exception:  # noqa
        raise
    else:
        return _rom_target_name(rom_inst), port
    finally:
        if rom_inst is not None:
            rom_inst._port.close()
