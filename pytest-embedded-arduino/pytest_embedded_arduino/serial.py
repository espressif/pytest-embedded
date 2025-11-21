import logging

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
        target: str | None = None,
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

        flash_settings = []
        for k, v in self.app.flash_settings.items():
            flash_settings.append(f'--{k}')
            flash_settings.append(v)

        if self.esp_flash_force:
            flash_settings.append('--force')

        try:
            esptool.main(
                [
                    '--chip',
                    self.app.target,
                    'write-flash',
                    '0x0',  # Merged binary is flashed at offset 0
                    self.app.binary_file,
                    *flash_settings,
                ],
                esp=self.esp,
            )
        except Exception:
            raise
