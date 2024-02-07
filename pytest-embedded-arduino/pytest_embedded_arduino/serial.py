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

    @EspSerial.use_esptool()
    def flash(self) -> None:
        """
        Flash the binary files to the board.
        """
        flash_files = []
        for offset, path, encrypted in self.app.flash_files:
            if encrypted:
                continue
            flash_files.extend((str(offset), path))

        flash_settings = []
        for k, v in self.app.flash_settings[self.app.target].items():
            flash_settings.append(f'--{k}')
            flash_settings.append(v)

        if self.esp_flash_force:
            flash_settings.append('--force')

        try:
            esptool.main(
                ['--chip', self.app.target, 'write_flash', *flash_files, *flash_settings],
                esp=self.esp,
            )
        except Exception:
            raise
