import contextlib
import hashlib
import logging
import os
import tempfile
from typing import Optional, TextIO, Union

import esptool
from pytest_embedded_serial_esp.serial import EspSerial

from .app import IdfApp


class IdfSerial(EspSerial):
    """
    IDF serial Dut class

    Auto flash the app while starting test.
    """

    SUGGEST_FLASH_BAUDRATE = 921600
    DEFAULT_SHA256_OFFSET = 0xB0

    def __init__(
        self,
        app: IdfApp,
        target: Optional[str] = None,
        confirm_target_elf_sha256: bool = False,
        erase_nvs: bool = False,
        **kwargs,
    ) -> None:
        self.app = app
        self.confirm_target_elf_sha256 = confirm_target_elf_sha256
        self.erase_nvs = erase_nvs

        if not hasattr(self.app, 'target'):
            raise ValueError(f"Idf app not parsable. Please check if it's valid: {self.app.binary_path}")

        if target and self.app.target and self.app.target != target:
            raise ValueError(f'Targets do not match. App target: {self.app.target}, Cmd target: {target}.')

        super().__init__(
            target=target or app.target,
            **kwargs,
        )

    def _post_init(self):
        if self.erase_all:
            self.skip_autoflash = False
        elif self._meta and self._meta.hit_port_app_cache(self.port, self.app):
            if self.confirm_target_elf_sha256:
                if self.is_target_flashed_same_elf():
                    logging.info('Confirmed target elf file sha256 the same as your local one.')
                    self.skip_autoflash = True
                else:
                    logging.info('target elf file is different from your local one. Flash the binary again.')
                    self.skip_autoflash = False
            else:
                logging.info(
                    'App is the same according to the session cache. '
                    'you can use flag "--confirm-target-elf-sha256" to make sure '
                    'that the target elf file is the same as your local one.'
                )
                self.skip_autoflash = True

        super()._post_init()

    def _start(self):
        if self.skip_autoflash:
            logging.info('Skipping auto flash...')
            super()._start()
        else:
            if self.app.is_loadable_elf:
                self.load_ram()
            else:
                self.flash()

    def load_ram(self) -> None:
        if not self.app.is_loadable_elf:
            raise ValueError('elf should be loadable elf')

        # 5.1 or earlier with sdkconfig APP_BUILD_TYPE_ELF_RAM, would build elf file only
        # 5.1 or later with sdkconfig renamed APP_BUILD_TYPE_RAM, would build bin file only
        if self.app.bin_file:
            bin_file = self.app.bin_file
        else:
            with contextlib.redirect_stdout(self._q):
                esptool.main(
                    [
                        '--chip',
                        self.app.target,
                        'elf2image',
                        self.app.elf_file,
                        *self.app.write_flash_args,
                    ],
                    esp=self.esp,
                )
            bin_file = self.app.elf_file.replace('.elf', '.bin')

        with contextlib.redirect_stdout(self._q):
            esptool.main(
                [
                    '--chip',
                    self.app.target,
                    '--no-stub',
                    'load_ram',
                    bin_file,
                ],
                esp=self.esp,
            )

    def _force_flag(self, app: Optional[IdfApp] = None):
        if self.esp_flash_force:
            return ['--force']

        if app is None:
            app = self.app

        if any((
            app.sdkconfig.get('SECURE_FLASH_ENC_ENABLED', False),
            app.sdkconfig.get('SECURE_BOOT', False),
        )):
            return ['--force']

        return []

    @EspSerial.use_esptool()
    def erase_flash(self, force: bool = False):
        if self._force_flag() or force:
            super().erase_flash(force=True)
        else:
            super().erase_flash()

    @EspSerial.use_esptool()
    def flash(self, app: Optional[IdfApp] = None) -> None:
        """
        Flash the `app.flash_files` to the dut
        """
        if not app:
            app = self.app

        if not app.flash_files:
            logging.error('No flash files detected. Skipping auto flash...')
            return

        if not app.flash_settings:
            logging.error('No flash settings detected. Skipping auto flash...')
            return

        _args = []
        for k, v in app.flash_args['extra_esptool_args'].items():
            if isinstance(v, bool):
                if k == 'stub':
                    if v is False:
                        _args.append('--no-stub')
                elif v:
                    _args.append(f'--{k}')
            else:
                _args.append(f'--{k}')
                if k == 'after':
                    _args.append('hard_reset')
                else:
                    _args.append(str(v))

        if '--baud' not in _args:
            _args.extend(['--baud', os.getenv('ESPBAUD', '921600')])
        _args.append('write_flash')

        if self.erase_nvs:
            esptool.main(
                [
                    'erase_region',
                    str(app.partition_table['nvs']['offset']),
                    str(app.partition_table['nvs']['size']),
                ],
                esp=self.esp,
            )
            self.esp.connect()

        encrypt_files = []
        flash_files = []
        for file in app.flash_files:
            if file.encrypted:
                encrypt_files.extend([hex(file.offset), str(file.file_path)])
            else:
                flash_files.extend([hex(file.offset), str(file.file_path)])

        if flash_files and encrypt_files:
            _args.extend([*flash_files, '--encrypt-files', *encrypt_files])
        else:
            if flash_files:
                _args.extend(flash_files)
            else:
                _args.extend(['--encrypt', *encrypt_files])

        _args.extend([*app.flash_args['write_flash_args'], *self._force_flag(app)])

        esptool.main(_args, esp=self.esp)

        if self._meta:
            self._meta.set_port_app_cache(self.port, app)

    @EspSerial.use_esptool()
    def dump_flash(
        self,
        partition: Optional[str] = None,
        address: Optional[str] = None,
        size: Optional[str] = None,
        output: Union[str, TextIO, None] = None,
    ) -> Optional[bytes]:
        """
        Dump the flash bytes into the output file by partition name or by start address and size.

        Args:
            output: file path or file stream to write to. File stream should be opened with bytes mode.
            partition: partition name
            address: address that start reading from
            size: read size

        Returns:
            None if `output` is `str` or file stream.
            bytes if `output` is None.
        """
        if partition:
            partition = self.app.partition_table[partition]
            _addr = partition['offset']
            _size = partition['size']
        elif address and size:
            _addr = address
            _size = size
        else:
            raise ValueError('You must specify "partition" or ("address" and "size") to dump flash')

        if output:
            esptool.main(['read_flash', str(_addr), str(_size), str(output)], esp=self.esp)
        else:
            with tempfile.NamedTemporaryFile() as fp:
                esptool.main(['read_flash', str(_addr), str(_size), fp.name], esp=self.esp)
                content = fp.read()
            return content

    @EspSerial.use_esptool()
    def erase_partition(self, partition_name: str) -> None:
        """
        Erase the partition provided

        Args:
            partition_name: partition name
        """
        if not self.app.partition_table:
            raise ValueError('Partition table not parsed.')

        if partition_name in self.app.partition_table:
            address = self.app.partition_table[partition_name]['offset']
            size = self.app.partition_table[partition_name]['size']
            logging.info(f'Erasing the partition "{partition_name}" of size {size} at {address}')
            esptool.main(['erase_region', str(address), str(size), *self._force_flag()], esp=self.esp)
        else:
            raise ValueError(f'partition name "{partition_name}" not found in app partition table')

    @EspSerial.use_esptool()
    def read_flash_elf_sha256(self) -> bytes:
        """
        Read the sha256 digest of the flashed elf file

        Returns:
            bytes of sha256
        """
        bin_offset = None
        for offset, filepath, _ in self.app.flash_files:
            if self.app.bin_file == filepath:
                bin_offset = offset
                break

        if not bin_offset:
            raise ValueError('.bin file not found in flash files')

        with tempfile.NamedTemporaryFile() as fp:
            esptool.main(
                ['read_flash', str(bin_offset + self.DEFAULT_SHA256_OFFSET), str(32), fp.name],
                esp=self.esp,
            )
            content = fp.read()
        return content

    def is_target_flashed_same_elf(self) -> bool:
        """
        Check if the sha256 values are matched between the flashed target and the `self.app.elf_file`

        Returns:
            True if the sha256 values are matched
        """
        if not self.app.elf_file:
            logging.info("no elf file. Can't tell if the target flashed the same elf file or not. Assume as False")
            return False

        flash_elf_sha256 = self.read_flash_elf_sha256()
        elf_sha256 = hashlib.sha256()
        with open(self.app.elf_file, 'rb') as fr:
            elf_sha256.update(fr.read())

        return flash_elf_sha256 == elf_sha256.digest()
