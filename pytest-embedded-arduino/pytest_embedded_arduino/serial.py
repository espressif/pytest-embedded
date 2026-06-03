import logging
import shutil
from pathlib import Path

import esptool
from pytest_embedded_serial_esp.serial import EspSerial

from .app import ArduinoApp

_ALWAYS_FLASH = {'boot_app0.bin'}
"""Binaries that must always be fully flashed (never receive a --diff-with ref).

boot_app0.bin selects the active OTA partition slot.  If the user performed an
OTA update since the last flash, the on-chip copy will differ from the reference
even though our local copy has not changed.
"""


class ArduinoSerial(EspSerial):
    """
    Arduino serial Dut class

    Auto flash the app while starting test.
    """

    SUGGEST_FLASH_BAUDRATE = 921600

    def __init__(
        self,
        app: ArduinoApp,
        target: str | None = None,
        fast_flash: bool = True,
        **kwargs,
    ) -> None:
        self.app = app
        self.fast_flash = fast_flash
        super().__init__(
            target=target or self.app.target,
            **kwargs,
        )

    def _ref_path(self, binary: str) -> Path:
        """Return the ``*_flashed.bin`` reference path for *binary* inside the build dir."""
        p = Path(binary)
        return Path(self.app.binary_path) / (p.stem + '_flashed' + p.suffix)

    @property
    def _ref_binaries(self) -> list[Path]:
        """All potential reference files for the current flash_files list."""
        return [self._ref_path(path) for _, path in self.app.flash_files]

    def _start(self):
        if self.skip_autoflash:
            logging.info('Skipping auto flash...')
            super()._start()
        else:
            self.flash()

    @EspSerial.use_esptool()
    def flash(self) -> None:
        """
        Flash individual binary files to the board.

        Uses esptool's ``--diff-with`` for fast reflashing when reference binaries
        from the previous successful flash are available, writing only changed
        4 KB sectors.  References are saved after each successful flash and
        invalidated by :meth:`erase_flash`.

        Unlike the merged-binary approach, individual binaries do not overlap
        with writable flash regions (NVS, OTA data, etc.), so the post-flash
        MD5 verification succeeds and ``--diff-with`` works correctly.
        """

        flash_settings = []
        for k, v in self.app.flash_settings.items():
            flash_settings.append(f'--{k}')
            flash_settings.append(v)

        if self.esp_flash_force:
            flash_settings.append('--force')

        addr_file_pairs: list[str] = []
        diff_args: list[str] = []
        have_any_ref = False

        for addr, binary in self.app.flash_files:
            addr_file_pairs.extend([addr, binary])

            if not self.fast_flash:
                continue

            name = Path(binary).name
            if name in _ALWAYS_FLASH:
                diff_args.append('skip')
                continue

            ref = self._ref_path(binary)
            if ref.exists():
                diff_args.append(str(ref))
                have_any_ref = True
            else:
                diff_args.append('skip')

        if self.fast_flash:
            if have_any_ref:
                logging.info(
                    'fast-flash: reflashing with references for %d/%d binaries',
                    sum(1 for d in diff_args if d != 'skip'),
                    len(diff_args),
                )
            else:
                diff_args = []
                logging.info('fast-flash: no references found, performing full flash')
        else:
            logging.info('fast-flash: disabled, performing full flash')

        diff_with = ['--diff-with', *diff_args] if diff_args else []

        try:
            esptool.main(
                [
                    '--chip',
                    self.app.target,
                    'write-flash',
                    *addr_file_pairs,
                    *flash_settings,
                    *diff_with,
                ],
                esp=self.esp,
            )
        except Exception:
            raise
        else:
            # Save copies of each binary as *_flashed.bin references so the
            # next invocation of flash() can pass them to --diff-with and only
            # write the 4 KB sectors that actually changed.
            if self.fast_flash:
                for _, binary in self.app.flash_files:
                    ref = self._ref_path(binary)
                    try:
                        if Path(binary).exists():
                            shutil.copy2(binary, ref)
                    except OSError as e:
                        logging.warning(
                            'fast-flash: could not save reference for %s (%s)',
                            Path(binary).name,
                            e,
                        )

    def erase_flash(self, force: bool = False) -> None:
        """
        Erase the complete flash and invalidate all fast-flash reference binaries.
        """
        super().erase_flash(force=force)
        if self.fast_flash:
            for ref in self._ref_binaries:
                if ref.exists():
                    try:
                        ref.unlink()
                        logging.debug('fast-flash: removed reference %s after erase', ref.name)
                    except OSError as e:
                        logging.warning('fast-flash: could not remove reference %s (%s)', ref.name, e)
