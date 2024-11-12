from typing import ClassVar, Dict, Optional

import esptool
from pytest_embedded_serial_esp.serial import EspSerial

from .app import NuttxApp


class NuttxSerial(EspSerial):
    """
    NuttX serial DUT class.
    """

    # Default offset for the primary MCUBoot slot across
    # all Espressif devices on NuttX
    MCUBOOT_PRIMARY_SLOT_OFFSET = 0x10000
    FLASH_BAUDRATE = 921600
    SERIAL_BAUDRATE = 115200

    binary_offsets: ClassVar[Dict[str, int]] = {
        'esp32': 0x1000,
        'esp32s2': 0x1000,
        'esp32c3': 0x0,
        'esp32s3': 0x0,
        'esp32c6': 0x0,
        'esp32h2': 0x0,
        'esp32p4': 0x2000,
    }

    def __init__(
        self,
        app: NuttxApp,
        target: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.app = app
        super().__init__(
            target=target or self.app.target,
            **kwargs,
        )

    @EspSerial.use_esptool()
    def flash(self) -> None:
        """Flash the binary files to the board."""

        flash_files = []
        if self.app.bootloader_file:
            flash_files.extend((str(self.binary_offsets[self.target]), self.app.bootloader_file.as_posix()))
            flash_files.extend((str(self.MCUBOOT_PRIMARY_SLOT_OFFSET), self.app.app_file.as_posix()))
        else:
            flash_files.extend((str(self.binary_offsets[self.target]), self.app.app_file.as_posix()))

        flash_settings = [
            '--flash_mode',
            self.app.flash_mode,
            '--flash_size',
            self.app.flash_size,
            '--flash_freq',
            self.app.flash_freq,
        ]

        esptool.main(
            [
                '--chip',
                self.app.target,
                '--port',
                self.port,
                '--baud',
                str(self.FLASH_BAUDRATE),
                'write_flash',
                *flash_files,
                *flash_settings,
            ],
            esp=self.esp,
        )
