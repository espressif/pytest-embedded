import logging
import os
import re
import tempfile
from contextlib import redirect_stdout

from pytest_embedded import PexpectProcess
from pytest_embedded_serial.dut import SerialDut

from .app import IdfApp
from .serial import IdfSerial


class IdfDut(SerialDut):
    XTENSA_TARGETS = ['esp32', 'esp32s2', 'esp32s3']
    RISCV32_TARGETS = ['esp32c3', 'esp32h2', 'esp32c2']

    COREDUMP_UART_START = b'================= CORE DUMP START ================='
    COREDUMP_UART_END = b'================= CORE DUMP END ================='
    COREDUMP_UART_REGEX = re.compile(COREDUMP_UART_START + b'(.+?)' + COREDUMP_UART_END, re.DOTALL)

    app: IdfApp
    serial: IdfSerial

    def __init__(
        self, pexpect_proc: PexpectProcess, app: IdfApp, serial: IdfSerial, skip_check_coredump: bool = False, **kwargs
    ) -> None:
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            app: `IdfApp` instance
            serial: `IdfSerial` instance
        """
        super().__init__(pexpect_proc, app, serial, **kwargs)

        self.target = serial.target
        self.skip_check_coredump = skip_check_coredump

    @property
    def toolchain_prefix(self) -> str:
        """
        Returns:
            Toolchain prefix according to the `self.target`
        """
        if self.target in self.XTENSA_TARGETS:
            return f'xtensa-{self.target}-elf-'
        elif self.target in self.RISCV32_TARGETS:
            return f'riscv32-{self.target}-elf-'
        else:
            raise ValueError(f'Unknown target: {self.target}')

    def _check_coredump(self) -> None:
        """
        Check core dumps via UART or partition table. Write the decoded or read core dumps into separated files.

        For UART, would read the `_pexpect_logfile` file.
        For partition, would read the flash according to the partition table. needs a valid `parttool_path`.

        Notes:
            - May include multiple core dumps, since each test case may include several unity test cases.
            - May have duplicated core dumps, since after the core dump happened, the target chip would reboot
            automatically.

        Returns:
            None
        """
        if self.app.sdkconfig.get('ESP_COREDUMP_ENABLE_TO_UART', False):
            self._dump_b64_coredumps()
        elif self.app.sdkconfig.get('ESP_COREDUMP_ENABLE_TO_FLASH', False):
            self._dump_flash_coredump()
        else:
            logging.debug('core dump disabled')

    def _dump_b64_coredumps(self) -> None:
        if not self.app.elf_file:
            logging.debug('no elf file. skipping dumping core dumps')
            return

        from esp_coredump import CoreDump  # need IDF_PATH

        with open(self.pexpect_proc._fr.name, 'rb') as fr:
            s = fr.read()

            for i, coredump in enumerate(set(self.COREDUMP_UART_REGEX.findall(s))):  # may duplicate
                coredump_file = None
                try:
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as coredump_file:
                        coredump_file.write(coredump.strip().replace(b'\r', b''))
                        coredump_file.flush()

                    coredump = CoreDump(
                        chip=self.target, core=coredump_file.name, core_format='b64', prog=self.app.elf_file
                    )
                    with open(os.path.join(self.logdir, f'coredump_output_{i}'), 'w') as fw:
                        with redirect_stdout(fw):
                            coredump.info_corefile()
                finally:
                    if coredump_file:
                        os.remove(coredump_file.name)

    def _dump_flash_coredump(self) -> None:
        if not self.app.elf_file:
            logging.debug('no elf file. skipping dumping core dumps')
            return

        from esp_coredump import CoreDump  # need IDF_PATH

        if self.app.sdkconfig['ESP_COREDUMP_DATA_FORMAT_ELF']:
            core_format = 'elf'
        elif self.app.sdkconfig['ESP_COREDUMP_DATA_FORMAT_BIN']:
            core_format = 'raw'
        else:
            raise ValueError(f'Invalid coredump format. Use _parse_b64_coredump for UART')

        with self.serial.disable_redirect_thread():
            coredump = CoreDump(
                chip=self.target,
                core_format=core_format,
                port=self.serial.port,
                prog=self.app.elf_file,
            )
            with open(os.path.join(self.logdir, f'coredump_output'), 'w') as fw:
                with redirect_stdout(fw):
                    coredump.info_corefile()

    def close(self) -> None:
        if not self.skip_check_coredump:
            self._check_coredump()
        super().close()
