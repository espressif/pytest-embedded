import logging
import typing as t

if t.TYPE_CHECKING:
    from pytest_embedded_idf.app import IdfApp

    from .espemu import EspEmu


class EspEmuSerial:
    """
    The device-state half of an emulated dut.

    ESP-IDF tests reach the chip through two channels: the console stream
    (``dut.expect``) and a control channel (``dut.serial``) that resets it,
    erases flash and burns eFuses. The second one is esptool-backed on
    hardware, and an emulator has no serial port behind it, so the operations
    that are expressible go over esp-emu's control channel instead.

    Reset and the flash erase and write operations go over the channel and act
    on the running machine, so the firmware sees them without a reload. The
    operations that need esptool itself — ``flash()``, ``bootloader_flash()``
    and the partition-writing helpers ESP-IDF's esp_tee tests subclass in —
    still raise, and the test reports the operation it needed.
    """

    def __init__(self, espemu: 'EspEmu', app: t.Optional['IdfApp'] = None) -> None:
        self.espemu = espemu
        self.app = app

    @property
    def port(self) -> str:
        """The control channel's address, in the place a port name would be."""
        if self.espemu.control_port is None:
            return 'espemu'
        return f'espemu://127.0.0.1:{self.espemu.control_port}'

    def hard_reset(self) -> None:
        """Reset the chip, the way a DTR/RTS toggle does on hardware."""
        logging.debug('hard resetting the emulated chip')
        self.espemu._hard_reset()

    def erase_flash(self) -> None:
        """Erase the whole flash, as ``esptool erase-flash`` does."""
        logging.info('erasing the emulated flash')
        self.espemu.control_command('erase-flash')

    def erase_region(self, offset: int, size: int) -> None:
        """Erase one flash region, as ``esptool erase-region`` does."""
        logging.info('erasing %#x bytes of emulated flash at %#x', size, offset)
        self.espemu.control_command(f'erase-region {offset:#x} {size:#x}')

    def erase_partition(self, partition_name: str) -> None:
        """Erase one partition, looked up in the app's partition table."""
        table = getattr(self.app, 'partition_table', None)
        if not table:
            raise ValueError('Partition table not parsed.')
        if partition_name not in table:
            raise ValueError(f'partition {partition_name} not found in the partition table')
        entry = table[partition_name]
        self.erase_region(entry['offset'], entry['size'])

    def write_flash_no_enc(self, offset: int, file_path: str) -> None:
        """Write one file into flash at ``offset``, without encrypting it."""
        logging.info('writing %s into emulated flash at %#x', file_path, offset)
        self.espemu.control_command(f'write-region {offset:#x} {file_path}')

    def close(self) -> None:
        """Nothing to close: the control channel is opened per command."""

    def __getattr__(self, name: str) -> t.Any:
        raise NotImplementedError(
            f'esp-emu cannot do dut.serial.{name}() yet. Only hard_reset is '
            f'implemented; flash and eFuse operations need the emulator in '
            f'download mode with its UART on a socket.'
        )
