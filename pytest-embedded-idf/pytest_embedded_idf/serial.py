import logging
import os
import tempfile
from typing import Optional

import esptool
import pexpect
from pytest_embedded.log import cls_redirect_stdout
from pytest_embedded_serial_esp.serial import EspSerial

from .app import IdfApp


class IdfSerial(EspSerial):
    """
    IDF serial Dut class

    Auto flash the app while starting test.
    """

    def __init__(
        self,
        app: IdfApp,
        target: Optional[str] = None,
        port: Optional[str] = None,
        pexpect_proc: Optional[pexpect.spawn] = None,
        **kwargs,
    ) -> None:
        self.app = app

        if target and self.app.target and self.app.target != target:
            raise ValueError(f'target not match. App target: {self.app.target}, Cmd target: {target}.')

        super().__init__(target or app.target, port, pexpect_proc, **kwargs)

    def _start(self):
        self.flash()

    @cls_redirect_stdout(source='flash')
    def flash(self, erase_nvs=True) -> None:
        """
        Flash the `app.flash_files` to the dut

        Args:
            erase_nvs: erase non-volatile storage blocks
        """
        if not self.app.partition_table:
            logging.error('Partition table not parsed. Skipping auto flash...')
            return

        last_error = None
        for baud_rate in [921600, 115200]:
            try:
                self._try_flash(erase_nvs, baud_rate)
                break
            except RuntimeError as e:
                last_error = e
        else:
            raise last_error

    @EspSerial._uses_esptool
    def _try_flash(self, erase_nvs=True, baud_rate=115200):
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
            self.stub.change_baud(baud_rate)
            esptool.detect_flash_size(self.stub, flash_args)
            esptool.write_flash(self.stub, flash_args)
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
