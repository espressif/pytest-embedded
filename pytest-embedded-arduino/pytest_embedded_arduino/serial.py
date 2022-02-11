import logging
from typing import Optional

import esptool
from pytest_embedded.log import PexpectProcess
from pytest_embedded_serial_esp.serial import EspSerial

from .app import ArduinoApp


class ArduinoSerial(EspSerial):
    """
    Arduino serial Dut class

    Auto flash the app while starting test.
    """

    SUGGEST_FLASH_BAUDRATE = 921600

    def __init__(
        self,
        pexpect_proc: PexpectProcess,
        app: ArduinoApp,
        port: Optional[str] = None,
        baud: int = EspSerial.DEFAULT_BAUDRATE,
        target: Optional[str] = None,
        skip_autoflash: bool = False,
        **kwargs,
    ) -> None:
        self.app = app
        super().__init__(pexpect_proc, target or self.app.target, port, baud, skip_autoflash, **kwargs)

    def _start(self):
        if self.skip_autoflash:
            logging.info('Skipping auto flash...')
            super()._start()
        else:
            self.flash()

    @EspSerial.use_esptool
    def flash(self) -> None:
        """
        Flash the binary files to the board.
        """
        flash_files = [
            (offset, open(path, 'rb')) for (offset, path, encrypted) in self.app.flash_files if not encrypted
        ]

        # fake flasher args object, this is a hack until
        # esptool Python API is improved
        class FlashArgs(object):
            def __init__(self, attributes):
                for key, value in attributes.items():
                    self.__setattr__(key, value)

        default_kwargs = {
            'addr_filename': flash_files,
            'encrypt_files': None,
            'no_stub': False,
            'compress': True,
            'verify': False,
            'ignore_flash_encryption_efuse_setting': False,
            'erase_all': False,
            'encrypt': False,
        }
        default_kwargs.update(self.app.flash_settings)
        flash_args = FlashArgs(default_kwargs)

        try:
            if self.proc.baudrate < self.SUGGEST_FLASH_BAUDRATE:
                self.stub.change_baud(self.SUGGEST_FLASH_BAUDRATE)

            esptool.detect_flash_size(self.stub, flash_args)
            esptool.write_flash(self.stub, flash_args)

            if self.proc.baudrate > self.DEFAULT_BAUDRATE:
                self.stub.change_baud(self.DEFAULT_BAUDRATE)
        except Exception:
            raise
        finally:
            for (_, f) in flash_files:
                f.close()
