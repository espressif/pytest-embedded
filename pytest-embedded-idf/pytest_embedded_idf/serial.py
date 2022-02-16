import hashlib
import logging
import os
import tempfile
from typing import Optional

import esptool
from pytest_embedded.log import PexpectProcess
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
        pexpect_proc: PexpectProcess,
        app: IdfApp,
        target: Optional[str] = None,
        port: Optional[str] = None,
        baud: int = EspSerial.DEFAULT_BAUDRATE,
        skip_autoflash: bool = False,
        **kwargs,
    ) -> None:
        self.app = app

        if not hasattr(self.app, 'target'):
            raise ValueError(f'Idf app not parsable. Please check if it\'s valid: {self.app.binary_path}')

        if target and self.app.target and self.app.target != target:
            raise ValueError(f'Targets do not match. App target: {self.app.target}, Cmd target: {target}.')

        super().__init__(pexpect_proc, target or app.target, port, baud, skip_autoflash, **kwargs)

    def _start(self):
        if self.skip_autoflash:
            logging.info('Skipping auto flash...')
            super()._start()
        else:
            self.flash()

    @EspSerial.use_esptool
    def flash(self, erase_nvs: bool = True) -> None:
        """
        Flash the `app.flash_files` to the dut

        Args:
            erase_nvs: erase non-volatile storage blocks
        """
        if not self.app.partition_table:
            logging.error('Partition table not parsed. Skipping auto flash...')
            return

        if not self.app.flash_files:
            logging.error('No flash files detected. Skipping auto flash...')
            return

        if not self.app.flash_settings:
            logging.error('No flash settings detected. Skipping auto flash...')
            return

        flash_files = [
            (offset, open(path, 'rb')) for (offset, path, encrypted) in self.app.flash_files if not encrypted
        ]
        encrypt_files = [(offset, open(path, 'rb')) for (offset, path, encrypted) in self.app.flash_files if encrypted]

        # fake flasher args object, this is a hack until
        # esptool Python API is improved
        class FlashArgs(object):
            def __init__(self, attributes):
                for key, value in attributes.items():
                    self.__setattr__(key, value)

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
        }
        default_kwargs.update(self.app.flash_settings)
        flash_args = FlashArgs(default_kwargs)

        nvs_file = None
        if erase_nvs:
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

        try:
            if self.proc.baudrate < self.SUGGEST_FLASH_BAUDRATE:
                self.stub.change_baud(self.SUGGEST_FLASH_BAUDRATE)

            esptool.detect_flash_size(self.stub, flash_args)
            esptool.write_flash(self.stub, flash_args)

            if self.proc.baudrate > self.DEFAULT_BAUDRATE:
                self.stub.change_baud(self.DEFAULT_BAUDRATE)  # set to the default one to get the serial output
        except Exception:  # noqa
            raise
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

    @EspSerial.use_esptool
    def dump_flash(
        self,
        output_filepath: str,
        partition: Optional[str] = None,
        address: Optional[str] = None,
        size: Optional[str] = None,
    ):
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
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
        with open(output_filepath, 'wb') as f:
            f.write(content)

    @EspSerial.use_esptool
    def read_flash_elf_sha256(self) -> bytes:
        bin_offset = None
        for offset, fn in self.app.flash_files:
            if self.app.bin_file == fn:
                bin_offset = offset
                break

        if not bin_offset:
            raise ValueError('.bin file not found in flash files')

        return self.stub.read_flash(bin_offset + self.DEFAULT_SHA256_OFFSET, 32)

    def is_target_flashed_same_elf(self) -> bool:
        flash_elf_sha256 = self.read_flash_elf_sha256()
        elf_sha256 = hashlib.sha256()
        with open(self.app.elf_file, 'rb') as fr:
            elf_sha256.update(fr.read())

        return flash_elf_sha256 == elf_sha256.digest()
