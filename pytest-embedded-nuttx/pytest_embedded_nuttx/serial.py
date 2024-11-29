from typing import ClassVar, Dict

import esptool
from esptool.cmds import FLASH_MODES, LoadFirmwareImage
from pytest_embedded_serial_esp.serial import EspSerial

from .app import NuttxApp
from .dut import NuttxSerialDut


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
        **kwargs,
    ) -> None:
        self.app = app
        super().__init__(**kwargs)
        self.flash_size = None
        self.flash_freq = None
        self.flash_mode = None
        self._get_binary_target_info()

    def _get_binary_target_info(self):
        """Binary target should be in the format nuttx.merged.bin, where
        the 'merged.bin' extension can be modified by the file_extension
        argument.

        Important note regarding MCUBoot:
        If enabled, the magic number will be on the MCUBoot binary. In this
        case, image_info should run on the mcuboot binary, not the NuttX one.
        """

        def get_key_from_value(dictionary, val):
            """Get key from value in dictionary"""
            for key, value in dictionary.items():
                if value == val:
                    return key
            return None

        binary_path = self.app.app_file
        if self.app.bootloader_file:
            binary_path = self.app.bootloader_file

        # Load app image and retrieve flash information
        image = LoadFirmwareImage(self.target, binary_path.as_posix())

        # Flash Size
        flash_s_bits = image.flash_size_freq & 0xF0
        self.flash_size = get_key_from_value(image.ROM_LOADER.FLASH_SIZES, flash_s_bits)

        # Flash Frequency
        flash_fr_bits = image.flash_size_freq & 0x0F  # low four bits
        self.flash_freq = get_key_from_value(image.ROM_LOADER.FLASH_FREQUENCY, flash_fr_bits)

        # Flash Mode
        self.flash_mode = get_key_from_value(FLASH_MODES, image.flash_mode)

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
            self.flash_mode,
            '--flash_size',
            self.flash_size,
            '--flash_freq',
            self.flash_freq,
        ]

        esptool.main(
            [
                '--chip',
                self.target,
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


class NuttxEspDut(NuttxSerialDut):
    """
    DUT class for serial ports connected to Espressif boards which are
    flashed with NuttX RTOS.
    """

    def __init__(
        self,
        app: NuttxApp,
        **kwargs,
    ) -> None:
        super().__init__(app=app, **kwargs)

    def reset(self) -> None:
        """Resets the board."""
        self.serial: NuttxSerial
        self.serial.hard_reset()
