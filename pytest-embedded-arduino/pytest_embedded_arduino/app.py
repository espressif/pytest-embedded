import json
import os
from typing import List, Optional, Tuple

from pytest_embedded.app import App


class ArduinoApp(App):
    """
    Arduino App class

    Attributes:
        app_path (str): Application path.
        build_dir (str): Build directory.
        sketch (str): Sketch name.
        fqbn (str): Fully Qualified Board Name.
        target (str) : ESPxx chip.
        flash_files (List[Tuple[int, str, str]]): List of (offset, file path, encrypted) of files need to be flashed in.
        flash_settings (dict[str, Any]): dict of flash settings
        binary_offsets (dict[str, List[int, int, int]]): dict of binaries' offset.
    """

    flash_settings = {'flash_mode': 'dio', 'flash_size': 'detect', 'flash_freq': '80m'}
    binary_offsets = {
        'esp32': [0x1000, 0x8000, 0x10000],
        'esp32s2': [0x1000, 0x8000, 0x10000],
        'esp32c3': [0x0, 0x8000, 0x10000],
        'esp32s3': [0x0, 0x8000, 0x10000],
    }

    def __init__(
        self,
        app_path: Optional[str] = None,
        build_dir: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            app_path (str): Application path.
            build_dir: Build directory.
        """

        super().__init__(app_path, build_dir, **kwargs)

        self.sketch = os.path.basename(app_path)
        self.fqbn = self._get_fqbn(self.binary_path)
        self.target = self.fqbn.split(':')[2]
        self.flash_files = self._get_bin_files(self.binary_path, self.sketch, self.target)

    def _get_fqbn(self, build_path) -> str:
        options_file = os.path.realpath(os.path.join(build_path, 'build.options.json'))
        with open(options_file) as f:
            options = json.load(f)
        fqbn = options['fqbn']
        return fqbn

    def _get_bin_files(self, build_path, sketch, target) -> List[Tuple[int, str, bool]]:
        bootloader = os.path.realpath(os.path.join(build_path, sketch + '.ino.bootloader.bin'))
        partitions = os.path.realpath(os.path.join(build_path, sketch + '.ino.partitions.bin'))
        app = os.path.realpath(os.path.join(build_path, sketch + '.ino.bin'))
        files = [bootloader, partitions, app]
        offsets = self.binary_offsets[target]
        return [(offsets[i], files[i], False) for i in range(3)]
