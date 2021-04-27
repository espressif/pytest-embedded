import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


class App:
    """
    Attributes which could be assigned from Pytest cli should be class attribute
    """
    FLASH_ARGS_FILENAME = 'flasher_args.json'

    def __init__(self, app_path: str = os.getcwd(),
                 parttool: Optional[str] = None):
        self.app_path = os.path.realpath(app_path)

        self.binary_path = self.get_binary_path()
        self.elf_file = self.get_elf_file()
        self.parttool_path = self.get_parttool_file(parttool)

        self.sdkconfig = self.parse_sdkconfig()  # type: Dict[str, Any]
        self.flash_files, self.flash_settings = self.parse_flash_args()
        self.partition_table = self.parse_partition_table()  # type: Dict[str, Any]

    def get_binary_path(self) -> str:
        path = os.path.join(self.app_path, 'build')

        if path and os.path.exists(path):
            return os.path.realpath(path)
        raise FileNotFoundError(f'Binary path "{path}" not found')  # TODO: maybe loose a bit?

    def get_elf_file(self) -> Optional[str]:
        for fn in os.listdir(self.binary_path):
            if os.path.splitext(fn)[-1] == '.elf':
                return os.path.realpath(os.path.join(self.binary_path, fn))
        return None

    def get_possible_sdkconfig_paths(self) -> List[str]:
        return [
            os.path.join(self.binary_path, '..', 'sdkconfig'),
            os.path.join(self.binary_path, 'sdkconfig'),
        ]

    def get_sdkconfig_file(self) -> Optional[str]:
        for file in self.get_possible_sdkconfig_paths():
            if os.path.isfile(file):
                return os.path.realpath(file)
        return None

    def parse_sdkconfig(self) -> Optional[Dict[str, Any]]:
        sdkconfig_filepath = self.get_sdkconfig_file()
        if not sdkconfig_filepath:
            return None

        res = {}
        with open(self.get_sdkconfig_file()) as fr:
            for line in fr:
                configs = line.split('=')
                if len(configs) == 2:
                    res[configs[0]] = configs[1].rstrip().strip('"')
        return res

    def get_flash_args_file(self) -> Optional[str]:
        for fn in os.listdir(self.binary_path):
            if fn == self.FLASH_ARGS_FILENAME:
                return os.path.realpath(os.path.join(self.binary_path, fn))
        return None

    def parse_flash_args(self) -> Tuple[Optional[List[Tuple[int, str]]], Optional[Dict[str, Any]]]:
        flash_args_filepath = self.get_flash_args_file()
        if not flash_args_filepath:
            return None, None

        with open(flash_args_filepath) as fr:
            flash_args = json.load(fr)

        flash_files = [(int(offs, 0), os.path.join(self.binary_path, file_path.strip()))
                       for (offs, file_path) in flash_args['flash_files'].items() if offs != '']
        flash_files = sorted(flash_files, key=lambda x: x[0])  # sort by offset

        flash_settings = flash_args['flash_settings']
        flash_settings['encrypt'] = 'CONFIG_SECURE_FLASH_ENCRYPTION_MODE_DEVELOPMENT' in self.sdkconfig
        return flash_files, flash_settings

    def get_parttool_file(self, parttool: Optional[str]) -> Optional[str]:
        parttool_filepath = parttool or os.path.join(os.getenv('IDF_PATH', ''), 'components', 'partition_table',
                                                     'gen_esp32part.py')
        if os.path.isfile(parttool_filepath):
            return os.path.realpath(parttool_filepath)
        return None

    def parse_partition_table(self) -> Optional[Dict[str, Any]]:
        if not (self.parttool_path and self.flash_files):
            return None

        errors = []
        for _, file in self.flash_files:
            if 'partition' in os.path.split(file)[1]:
                partition_file = os.path.join(self.binary_path, file)
                process = subprocess.Popen([sys.executable, self.parttool_path, partition_file],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (raw_data, raw_error) = process.communicate()
                if isinstance(raw_error, bytes):
                    raw_error = raw_error.decode()
                if 'Traceback' in raw_error:
                    # Some exception occurred. It is possible that we've tried the wrong binary file.
                    errors.append((file, raw_error))
                    continue
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode()
                break
        else:
            traceback_msg = '\n'.join([f'{self.parttool_path} {p}:{os.linesep}{msg}' for p, msg in errors])
            raise ValueError(f'No partition table found under {self.binary_path}\n'
                             f'{traceback_msg}')

        partition_table = {}
        for line in raw_data.splitlines():
            if line[0] != '#':
                try:
                    _name, _type, _subtype, _offset, _size, _flags = line.split(',')
                    if _size[-1] == 'K':
                        _size = int(_size[:-1]) * 1024
                    elif _size[-1] == 'M':
                        _size = int(_size[:-1]) * 1024 * 1024
                    else:
                        _size = int(_size)
                    _offset = int(_offset, 0)
                except ValueError:
                    continue
                partition_table[_name] = {
                    'type': _type,
                    'subtype': _subtype,
                    'offset': _offset,
                    'size': _size,
                    'flags': _flags
                }
        return partition_table
