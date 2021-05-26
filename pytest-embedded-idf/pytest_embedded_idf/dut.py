import os
import tempfile

import esptool
from pytest_embedded.dut import Dut
from pytest_embedded_serial_esp.dut import EspSerialDut

from .app import IdfApp


class IdfSerialDut(EspSerialDut):
    """
    IDF serial dut class

    Auto flash the app while starting test.
    """

    def _start(self):
        self.flash()

    @Dut.redirect_stdout('flash')
    def flash(self, erase_nvs=True) -> None:
        """
        Flash the :attr:`flash_files` and :attr:`encrypt_files` of :attr:`self.app`

        :param erase_nvs: erase non-volatile storage blocks
        """
        last_error = None
        for baud_rate in [921600, 115200]:
            try:
                self._try_flash(erase_nvs, baud_rate)
                break
            except RuntimeError as e:
                last_error = e
        else:
            raise last_error

    @EspSerialDut._uses_esptool
    def _try_flash(self, stub_inst: esptool.ESPLoader, erase_nvs=True, baud_rate=115200):
        self.app: IdfApp

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
