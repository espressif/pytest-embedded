import functools
import logging
import os
import sys
from typing import List, Optional, Tuple

import esptool
import pexpect
from pytest_embedded.app import App
from pytest_embedded.log import cls_redirect_stdout
from pytest_embedded_serial.dut import Serial
from serial.tools.list_ports_posix import comports


class EspSerial(Serial):
    """
    Serial class for ports connected to espressif products
    """

    def __init__(
        self,
        target: Optional[App] = None,
        port: Optional[str] = None,
        pexpect_proc: Optional[pexpect.spawn] = None,
        **kwargs,
    ) -> None:

        self.pexpect_proc = pexpect_proc  # let the pexpect_proc work in `detect_target_port()` as well

        target, port = self.detect_target_port(target, port)
        logging.info(f'Target: {target}, Port: {port}')

        self.target = target
        self.rom: Optional[esptool.ESPLoader] = None
        self.stub: Optional[esptool.ESPLoader] = None

        super().__init__(port, pexpect_proc, **kwargs)

    def _uses_esptool(func):
        """
        Provided functionalities:
        - run hard_reset before real function run
        - reset the port settings after real function run
        - call `run_stub()` and pass the ESPStubLoader instance
        """

        @functools.wraps(func)
        def handler(self, *args, **kwargs):
            settings = self.proc.get_settings()

            if self.rom is None:
                self.rom = esptool.ESPLoader.detect_chip(self.proc)

            try:
                self.rom.connect('hard_reset')
                self.stub = self.rom.run_stub()

                ret = func(self, *args, **kwargs)

                # do hard reset after use esptool
                self.stub.hard_reset()
            finally:
                self.proc.apply_settings(settings)
            return ret

        return handler

    def _start(self):
        self.hard_reset()

    @_uses_esptool
    def hard_reset(self):
        """
        Hard reset via esptool
        """
        pass

    @cls_redirect_stdout(source='detecting port')
    def detect_target_port(self, target: Optional[str] = None, port: Optional[str] = None) -> Tuple[str, str]:
        """
        Returns the target chip type and port. Will do auto-detection if argument `target` or `port` or both of
        them are missing.

        Args:
            target: serial target chip type
            port: serial port

        Returns:
            detected chip type and port
        """
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
