import contextlib
import functools
import logging
import subprocess

import esptool
from esptool import __version__ as ESPTOOL_VERSION
from esptool.targets import CHIP_LIST as ESPTOOL_CHIPS
from pexpect import TIMEOUT
from pytest_embedded.log import MessageQueue, PexpectProcess, live_print_call
from pytest_embedded.utils import Meta
from pytest_embedded_serial.dut import Serial


def _is_port_mac_verified(pexpect_proc: PexpectProcess, port: str, port_mac: str, msg_queue) -> bool:
    try:
        live_print_call(['esptool.py', '--port', port, 'read_mac'], msg_queue=msg_queue)
    except subprocess.CalledProcessError:
        return False
    else:
        try:
            pexpect_proc.expect(f'MAC: {port_mac.lower()}', timeout=0.1)
        except TIMEOUT:
            return False
        else:
            return True


class EspSerial(Serial):
    """
    Serial class for ports connected to espressif products
    """

    ESPTOOL_DEFAULT_BAUDRATE = 921600

    def __init__(
        self,
        pexpect_proc: PexpectProcess,
        msg_queue: MessageQueue,
        target: str | None = None,
        beta_target: str | None = None,
        port: str | None = None,
        port_serial_number: str | None = None,
        port_mac: str | None = None,
        baud: int = Serial.DEFAULT_BAUDRATE,
        esptool_baud: int = ESPTOOL_DEFAULT_BAUDRATE,
        esp_flash_force: bool = False,
        skip_autoflash: bool = False,
        erase_all: bool = False,
        meta: Meta | None = None,
        ports_to_occupy: list[str] = (),
        **kwargs,
    ) -> None:
        self._meta = meta
        filters = {}
        if port_serial_number:
            filters['serials'] = [s.strip() for s in port_serial_number.split(',') if s.strip()]

        esptool_target = beta_target or target or 'auto'
        if port is None or port.endswith('*'):
            port_filter = port.strip('*') if port else ''
            available_ports = [_p for _p in esptool.get_port_list(**filters) if port_filter in _p]
            ports = list(set(available_ports) - set(self.occupied_ports.keys()) - set(ports_to_occupy))

            # sort to make /dev/ttyS* ports before /dev/ttyUSB* ports
            # esptool will reverse the list
            ports.sort()
            if port_mac:
                for port in ports:
                    if _is_port_mac_verified(pexpect_proc, port, port_mac, msg_queue):
                        ports = [port]
                        break
                else:
                    raise ValueError(f'The specified MAC address {port_mac} cannot be found.')

            # prioritize the cache recorded target port
            if esptool_target and self._meta:
                ports.sort(key=lambda x: self._meta.hit_port_target_cache(x, esptool_target))

            logging.debug(f'Detecting ports from {", ".join(ports)}')
        else:
            if port_mac:
                if _is_port_mac_verified(pexpect_proc, port, port_mac, msg_queue):
                    ports = [port]
                else:
                    raise ValueError(f'The specified MAC address {port_mac} binds with different port, not with {port}')
            else:
                ports = [port]

        # normal loader
        if esptool_target not in ['auto', *ESPTOOL_CHIPS]:
            raise ValueError(
                f'esptool version {ESPTOOL_VERSION} not support target {esptool_target}\n'
                f'Supported targets: {ESPTOOL_CHIPS}'
            )

        with contextlib.redirect_stdout(msg_queue):
            self.esp = esptool.get_default_connected_device(
                ports,
                port=port,
                connect_attempts=3,
                initial_baud=baud,
                chip=esptool_target,
            )

        if not self.esp:
            raise ValueError('Couldn\'t auto detect chip. Please manually specify with "--port"')

        target = self.esp.CHIP_NAME.lower().replace('-', '')
        logging.info('Target: %s, Port: %s', target, self.esp.serial_port)

        self.target = target

        self.skip_autoflash = skip_autoflash
        self.erase_all = erase_all
        self.esptool_baud = esptool_baud
        self.esp_flash_force = esp_flash_force

        super().__init__(
            msg_queue=msg_queue, port=self.esp._port, baud=baud, meta=meta, ports_to_occupy=ports_to_occupy, **kwargs
        )

    def _post_init(self):
        if self._meta:
            self._meta.set_port_target_cache(self.port, self.target)

        if self.erase_all:
            esptool.main(['erase-flash'], esp=self.esp)

        super()._post_init()

    @staticmethod
    def use_esptool():
        """
        1. tell the redirect serial thread to stop reading from the `pyserial` instance
        2. esptool reuse the `pyserial` instance and call `esptool.main()` to do the actual work
        3. tell the redirect serial thread to continue reading from serial
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                with self.disable_redirect_thread():
                    with contextlib.redirect_stdout(self._q):
                        settings = self.proc.get_settings()
                        self.esp.connect()
                        ret = func(self, *args, **kwargs)
                        self.proc.apply_settings(settings)
                return ret

            return wrapper

        return decorator

    def _start(self):
        self.hard_reset()

    def hard_reset(self):
        """Hard reset your espressif device"""
        self.esp.hard_reset()

    @use_esptool()
    def erase_flash(self, force: bool = False) -> None:
        """Erase the complete flash"""
        logging.info('Erasing the flash')
        options = ['erase-flash']

        if force or self.esp_flash_force:
            options.append('--force')

        esptool.main(options, esp=self.esp)

        if self._meta:
            self._meta.drop_port_app_cache(self.port)
