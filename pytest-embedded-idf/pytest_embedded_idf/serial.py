import hashlib
import logging
import os
import tempfile
from typing import Optional, TextIO, Union

import esptool
from pytest_embedded.log import live_print_call
from pytest_embedded_serial_esp.serial import EspSerial, EsptoolArgs

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
            raise ValueError(f'Idf app not parsable. Please check if it\'s valid: {self.app.binary_path}')

        if target and self.app.target and self.app.target != target:
            raise ValueError(f'Targets do not match. App target: {self.app.target}, Cmd target: {target}.')

        super().__init__(
            target=target or app.target,
            **kwargs,
        )

    def _post_init(self):
        if self._meta and self.port in self._meta.port_app_cache:
            if self.app.binary_path == self._meta.port_app_cache[self.port]:  # hit the cache
                logging.debug('hit port-app cache: %s - %s', self.port, self.app.binary_path)
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

        live_print_call(
            [
                'esptool.py',
                '--chip',
                self.app.target,
                'elf2image',
                self.app.elf_file,
                *self.app._parse_flash_args(),
            ],
            msg_queue=self._q,
        )
        live_print_call(
            [
                'esptool.py',
                '--chip',
                self.app.target,
                '--no-stub',
                'load_ram',
                self.app.elf_file.replace('.elf', '.bin'),
            ],
            msg_queue=self._q,
        )

    @EspSerial.use_esptool()
    def flash(self) -> None:
        """
        Flash the `app.flash_files` to the dut
        """
        if not self.app.flash_files:
            logging.error('No flash files detected. Skipping auto flash...')
            return

        if not self.app.flash_settings:
            logging.error('No flash settings detected. Skipping auto flash...')
            return

        flash_files = [(file.offset, open(file.file_path, 'rb')) for file in self.app.flash_files if not file.encrypted]
        encrypt_files = [(file.offset, open(file.file_path, 'rb')) for file in self.app.flash_files if file.encrypted]

        nvs_file = None
        try:
            if self.erase_nvs:
                address = self.app.partition_table['nvs']['offset']
                size = self.app.partition_table['nvs']['size']
                nvs_file = tempfile.NamedTemporaryFile(delete=False)
                nvs_file.write(b'\xff' * size)
                if not isinstance(address, int):
                    address = int(address, 0)

                if self.app.flash_settings['encrypt']:
                    encrypt_files.append((address, open(nvs_file.name, 'rb')))
                else:
                    flash_files.append((address, open(nvs_file.name, 'rb')))

            # write_flash expects the parameter encrypt_files to be None and not
            # an empty list, so perform the check here
            default_kwargs = {
                'addr_filename': flash_files,
                'encrypt_files': encrypt_files or None,
                'no_stub': False,
                'compress': True,
                'verify': False,
                'ignore_flash_encryption_efuse_setting': False,
                'erase_all': False,
                'force': False,
            }

            if self.erase_all:
                default_kwargs['erase_all'] = True

            default_kwargs.update(self.app.flash_settings)
            default_kwargs.update(self.app.flash_args.get('extra_esptool_args', {}))
            args = EsptoolArgs(**default_kwargs)

            self.stub.change_baud(self.esptool_baud)
            esptool.detect_flash_size(self.stub, args)
            esptool.write_flash(self.stub, args)
            self.stub.change_baud(self.baud)

            logging.debug('set port-app cache: %s - %s', self.port, self.app.binary_path)
            self._meta.port_app_cache[self.port] = self.app.binary_path
        finally:
            if nvs_file:
                nvs_file.close()
                try:
                    os.remove(nvs_file.name)
                except OSError:
                    pass
            for (_, f) in flash_files:
                f.close()
            for (_, f) in encrypt_files:
                f.close()

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

        content = self.stub.read_flash(_addr, _size)
        if output:
            if isinstance(output, str):
                os.makedirs(os.path.dirname(output), exist_ok=True)
                with open(output, 'wb') as f:
                    f.write(content)
            else:
                output.write(content)
        else:
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
            self.stub.erase_region(address, size)
        else:
            raise ValueError(f'partition name "{partition_name}" not found in app partition table')

    @EspSerial.use_esptool()
    def erase_flash(self) -> None:
        """
        Erase the complete flash
        """
        logging.info('Erasing the flash')
        self.stub.erase_flash()

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

        return self.stub.read_flash(bin_offset + self.DEFAULT_SHA256_OFFSET, 32)

    def is_target_flashed_same_elf(self) -> bool:
        """
        Check if the sha256 values are matched between the flashed target and the `self.app.elf_file`

        Returns:
            True if the sha256 values are matched
        """
        if not self.app.elf_file:
            logging.info('no elf file. Can\'t tell if the target flashed the same elf file or not. Assume as False')
            return False

        flash_elf_sha256 = self.read_flash_elf_sha256()
        elf_sha256 = hashlib.sha256()
        with open(self.app.elf_file, 'rb') as fr:
            elf_sha256.update(fr.read())

        return flash_elf_sha256 == elf_sha256.digest()
