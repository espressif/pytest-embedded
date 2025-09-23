import logging
from pathlib import Path

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

        self.file_extension = file_extension
        self.app_file, self.bootloader_file, self.merge_file, self.vefuse_file = self._get_bin_files()

    def _get_bin_files(self) -> tuple[Path | None, Path | None, Path | None, Path | None]:
        """
        Get path to binary files available in the app_path.
        If either the application image or bootloader is not found,
        None is returned.

        Returns:
            tuple: path to application binary file and bootloader file.
        """
        search_path = Path(self.app_path)
        search_pattern = '*' + self.file_extension
        bin_files = list(search_path.rglob(search_pattern))
        app_file, bootloader_file, merge_file = None, None, None
        vefuse_file = None

        logging.info('Searching %s', str(search_path))
        if not bin_files:
            logging.warning('No binary files found with pattern: %s', search_pattern)

        for file_path in bin_files:
            file_name = str(file_path.stem)
            if 'vefuse' in file_name:
                vefuse_file = file_path
                logging.info('Virtual E-Fuse file: %s', vefuse_file.as_posix())
            if 'nuttx' in file_name:
                if 'merged' in file_name:
                    merge_file = file_path
                    logging.info('Merge file: %s', merge_file.as_posix())
                else:
                    app_file = file_path
                    logging.info('App file: %s', app_file.as_posix())
            if 'mcuboot-' in file_name:
                bootloader_file = file_path
                logging.info('Bootloader file: %s', bootloader_file.as_posix())

        if not app_file:
            logging.error('App file not found: %s', app_file)
            print(bin_files)

        return app_file, bootloader_file, merge_file, vefuse_file
