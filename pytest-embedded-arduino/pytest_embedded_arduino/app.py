import json
import os
from typing import ClassVar

from pytest_embedded.app import App


class ArduinoApp(App):
    """
    Arduino App class

    Attributes:
        sketch (str): Sketch name.
        fqbn (str): Fully Qualified Board Name.
        target (str) : ESPxx chip.
        flash_files (List[Tuple[int, str, str]]): List of (offset, file path, encrypted) of files need to be flashed in.
    """

    #: dict of flash settings
    flash_settings: ClassVar[dict[str, dict[str, str]]] = {
        'esp32': {'flash_mode': 'dio', 'flash_size': 'detect', 'flash_freq': '80m'},
        'esp32s2': {'flash_mode': 'dio', 'flash_size': 'detect', 'flash_freq': '80m'},
        'esp32c3': {'flash_mode': 'dio', 'flash_size': 'detect', 'flash_freq': '80m'},
        'esp32s3': {'flash_mode': 'dio', 'flash_size': 'detect', 'flash_freq': '80m'},
        'esp32c6': {'flash_mode': 'dio', 'flash_size': 'detect', 'flash_freq': '80m'},
        'esp32h2': {'flash_mode': 'dio', 'flash_size': 'detect', 'flash_freq': '48m'},
        'esp32p4': {'flash_mode': 'dio', 'flash_size': 'detect', 'flash_freq': '80m'},
    }

    #: dict of binaries' offset.
    binary_offsets: ClassVar[dict[str, list[int]]] = {
        'esp32': [0x1000, 0x8000, 0x10000],
        'esp32s2': [0x1000, 0x8000, 0x10000],
        'esp32c3': [0x0, 0x8000, 0x10000],
        'esp32s3': [0x0, 0x8000, 0x10000],
        'esp32c6': [0x0, 0x8000, 0x10000],
        'esp32h2': [0x0, 0x8000, 0x10000],
        'esp32p4': [0x2000, 0x8000, 0x10000],
    }

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.sketch = os.path.basename(self.app_path)
        self.fqbn = self._get_fqbn(self.binary_path)
        self.target = self.fqbn.split(':')[2]
        self.flash_files = self._get_bin_files(self.binary_path, self.sketch, self.target)
        self.elf_file = os.path.realpath(os.path.join(self.binary_path, self.sketch + '.ino.elf'))

    def _get_fqbn(self, build_path) -> str:
        options_file = os.path.realpath(os.path.join(build_path, 'build.options.json'))
        with open(options_file) as f:
            options = json.load(f)
        fqbn = options['fqbn']
        return fqbn

    def _get_bin_files(self, build_path, sketch, target) -> list[tuple[int, str, bool]]:
        bootloader = os.path.realpath(os.path.join(build_path, sketch + '.ino.bootloader.bin'))
        partitions = os.path.realpath(os.path.join(build_path, sketch + '.ino.partitions.bin'))
        app = os.path.realpath(os.path.join(build_path, sketch + '.ino.bin'))
        files = [bootloader, partitions, app]
        offsets = self.binary_offsets[target]
        return [(offsets[i], files[i], False) for i in range(3)]
