import logging
from typing import Optional

import esptool
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
        app: ArduinoApp,
        target: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.app = app
        super().__init__(
            target=target or self.app.target,
            **kwargs,
        )

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
            'force': False,
            'chip': self.app.target,
        }

        if self.erase_all:
            default_kwargs['erase_all'] = True

        default_kwargs.update(self.app.flash_settings)
        flash_args = FlashArgs(default_kwargs)

        try:
            self.stub.change_baud(self.esptool_baud)
            esptool.detect_flash_size(self.stub, flash_args)
            esptool.write_flash(self.stub, flash_args)
            self.stub.change_baud(self.baud)
        except Exception:
            raise
        finally:
            for (_, f) in flash_files:
                f.close()
