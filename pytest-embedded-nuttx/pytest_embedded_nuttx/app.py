import logging
from pathlib import Path

from esptool.cmds import FLASH_MODES, LoadFirmwareImage
from pytest_embedded.app import App


class NuttxApp(App):
    """
    NuttX App class for Espressif devices.
    Evaluates binary files (firmware and bootloader) and extract information
    required for flashing.

    Attributes:
        file_extension (str): app binary file extension.
    """

    def __init__(
        self,
        file_extension='.bin',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.flash_size = None
        self.flash_freq = None
        self.flash_mode = None
        self.file_extension = file_extension
        files = self._get_bin_files()
        self.app_file, self.bootloader_file, self.merge_file = files
        self._get_binary_target_info()

    def _get_bin_files(self) -> list:
        """
        Get path to binary files available in the app_path.
        If either the application image or bootloader is not found,
        None is returned.

        Returns:
            list: path to application binary file and bootloader file.
        """
        search_path = Path(self.app_path)
        search_pattern = '*' + self.file_extension
        bin_files = list(search_path.rglob(search_pattern))
        app_file, bootloader_file, merge_file = None, None, None

        logging.info('Searching %s', str(search_path))
        if not bin_files:
            logging.warning('No binary files found with pattern: %s', search_pattern)

        for file_path in bin_files:
            file_name = str(file_path.stem)
            if 'nuttx' in file_name:
                if 'merged' in file_name:
                    merge_file = file_path
                else:
                    app_file = file_path
            if 'mcuboot-' in file_name:
                bootloader_file = file_path

        if not app_file:
            logging.error('App file not found: %s', app_file)
            print(bin_files)

        return app_file, bootloader_file, merge_file

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

        binary_path = self.app_file
        if self.bootloader_file:
            binary_path = self.bootloader_file

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
