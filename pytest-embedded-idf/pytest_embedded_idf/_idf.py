import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import esptool
from pytest_embedded.app import App
from pytest_embedded_serial._serial import SerialDut


class IdfApp(App):
    FLASH_ARGS_FILENAME = 'flasher_args.json'

    def __init__(self, app_path: str = os.getcwd(), part_tool: Optional[str] = None, *args, **kwargs):
        super().__init__(app_path, *args, **kwargs)
        self.binary_path = self._get_binary_path()
        if not self.binary_path:
            return

        self.elf_file = self._get_elf_file()
        self.parttool_path = self._get_parttool_file(part_tool)

        self.sdkconfig = self._parse_sdkconfig()  # type: Dict[str, Any]
        self.flash_files, self.encrypt_files, self.flash_settings = self._parse_flash_args()
        self.partition_table = self._parse_partition_table()  # type: Dict[str, Any]

        self.target = self._get_target_from_sdkconfig()

    def _get_binary_path(self) -> Optional[str]:
        path = os.path.join(self.app_path, 'build')

        if path and os.path.exists(path):
            return os.path.realpath(path)
        logging.warning(f'{path} not exists')
        return None

    def _get_elf_file(self) -> Optional[str]:
        for fn in os.listdir(self.binary_path):
            if os.path.splitext(fn)[-1] == '.elf':
                return os.path.realpath(os.path.join(self.binary_path, fn))
        return None

    def _get_possible_sdkconfig_paths(self) -> List[str]:
        return [
            os.path.join(self.binary_path, '..', 'sdkconfig'),
            os.path.join(self.binary_path, 'sdkconfig'),
        ]

    def _get_sdkconfig_file(self) -> Optional[str]:
        for file in self._get_possible_sdkconfig_paths():
            if os.path.isfile(file):
                return os.path.realpath(file)
        return None

    def _parse_sdkconfig(self) -> Optional[Dict[str, Any]]:
        sdkconfig_filepath = self._get_sdkconfig_file()
        if not sdkconfig_filepath:
            return None

        res = {}
        with open(self._get_sdkconfig_file()) as fr:
            for line in fr:
                configs = line.split('=')
                if len(configs) == 2:
                    res[configs[0]] = configs[1].rstrip().strip('"')
        return res

    def _get_flash_args_file(self) -> Optional[str]:
        for fn in os.listdir(self.binary_path):
            if fn == self.FLASH_ARGS_FILENAME:
                return os.path.realpath(os.path.join(self.binary_path, fn))
        return None

    def _is_encrypted(self, flash_args, offs, file_path):
        for entry in flash_args.values():
            try:
                if (entry['offset'], entry['file']) == (offs, file_path):
                    return entry['encrypted'] == 'true'
            except (TypeError, KeyError):
                continue

        return None

    def _parse_flash_args(self) -> Tuple[Optional[List[Tuple[int, str]]],
                                         Optional[List[Tuple[int, str]]],
                                         Optional[Dict[str, Any]]]:
        flash_args_filepath = self._get_flash_args_file()
        if not flash_args_filepath:
            return None, None, None

        default_encryption = 'CONFIG_SECURE_FLASH_ENCRYPTION_MODE_DEVELOPMENT' in self.sdkconfig
        with open(flash_args_filepath) as fr:
            flash_args = json.load(fr)

        flash_files = []
        encrypt_files = []
        for (offs, file_path) in flash_args['flash_files'].items():
            if not offs:
                continue

            flash_files.append((int(offs, 0), os.path.join(self.binary_path, file_path)))
            encrypted = self._is_encrypted(flash_args, offs, file_path)

            if (encrypted is None and default_encryption) or encrypted:
                encrypt_files.append((int(offs, 0), os.path.join(self.binary_path, file_path)))

        flash_files = sorted(flash_files)
        encrypt_files = sorted(encrypt_files)
        flash_settings = flash_args['flash_settings']
        flash_settings['encrypt'] = (flash_files == encrypt_files)

        return flash_files, encrypt_files, flash_settings

    def _get_parttool_file(self, parttool: Optional[str]) -> Optional[str]:
        parttool_filepath = parttool or os.path.join(os.getenv('IDF_PATH', ''), 'components', 'partition_table',
                                                     'gen_esp32part.py')
        if os.path.isfile(parttool_filepath):
            return os.path.realpath(parttool_filepath)
        return None

    def _parse_partition_table(self) -> Optional[Dict[str, Any]]:
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

    def _get_target_from_sdkconfig(self):
        return self.sdkconfig.get('CONFIG_IDF_TARGET', 'esp32')


class IdfSerialDut(SerialDut):
    def start(self):
        self.flash()

    def flash(self, erase_nvs=True):
        last_error = None
        for baud_rate in [921600, 115200]:
            try:
                self._try_flash(erase_nvs, baud_rate)
                break
            except RuntimeError as e:
                last_error = e
        else:
            raise last_error

    @SerialDut._uses_esptool
    def _try_flash(self, stub_inst: esptool.ESPLoader, erase_nvs=True, baud_rate=115200):
        self.app: IdfApp

        flash_files = self.app.flash_files
        encrypt_files = self.app.encrypt_files
        encrypt = self.app.flash_settings.get('encrypt', False)
        if encrypt:
            flash_files = encrypt_files
            encrypt_files = []
        else:
            flash_files = [entry for entry in flash_files if entry not in encrypt_files]

        flash_files = [(offs, open(path, 'rb')) for (offs, path) in flash_files]
        encrypt_files = [(offs, open(path, 'rb')) for (offs, path) in encrypt_files]

        # fake flasher args object, this is a hack until
        # esptool Python API is improved
        class FlashArgs(object):
            def __init__(self, attributes):
                for key, value in attributes.items():
                    self.__setattr__(key, value)

        # write_flash expects the parameter encrypt_files to be None and not
        # an empty list, so perform the check here
        flash_args = FlashArgs({
            'flash_size': self.app.flash_settings['flash_size'],
            'flash_mode': self.app.flash_settings['flash_mode'],
            'flash_freq': self.app.flash_settings['flash_freq'],
            'addr_filename': flash_files,
            'encrypt_files': encrypt_files or None,
            'no_stub': False,
            'compress': True,
            'verify': False,
            'encrypt': encrypt,
            'ignore_flash_encryption_efuse_setting': False,
            'erase_all': False,
        })

        nvs_file = None
        if erase_nvs:
            address = self.app.partition_table['nvs']['offset']
            size = self.app.partition_table['nvs']['size']
            nvs_file = tempfile.NamedTemporaryFile(delete=False)
            nvs_file.write(b'\xff' * size)
            if not isinstance(address, int):
                address = int(address, 0)

            if encrypt:
                encrypt_files.append((address, open(nvs_file.name, 'rb')))
            else:
                flash_files.append((address, open(nvs_file.name, 'rb')))

        try:
            stub_inst.change_baud(baud_rate)
            esptool.detect_flash_size(stub_inst, flash_args)
            esptool.write_flash(stub_inst, flash_args)
        except Exception:  # noqa
            raise
        finally:
            if nvs_file:
                nvs_file.close()
                os.remove(nvs_file.name)
            for (_, f) in flash_files:
                f.close()
            for (_, f) in encrypt_files:
                f.close()
