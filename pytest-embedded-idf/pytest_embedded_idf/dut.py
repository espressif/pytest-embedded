import importlib.util
import logging
import os
import re
import subprocess
import sys
import tempfile
import typing as t
import warnings
from contextlib import redirect_stdout

from pytest_embedded.utils import UserHint, to_str
from pytest_embedded_serial.dut import SerialDut
from pytest_embedded_serial_esp import EspSerial

from .app import IdfApp
from .unity_tester import (
    IdfUnityDutMixin,
    UnittestMenuCase,  # noqa # keep backward compatibility
)


class IdfDut(IdfUnityDutMixin, SerialDut):
    """
    Dut class for serial ports connect to Espressif boards which are flashed with ESP-IDF apps

    Attributes:
        target (str): target chip type
        skip_check_coredump (bool): skip check core dumped or not while dut teardown if set to True
    """

    XTENSA_TARGETS = IdfApp.XTENSA_TARGETS
    RISCV32_TARGETS = IdfApp.RISCV32_TARGETS

    COREDUMP_UART_START = b'================= CORE DUMP START ================='
    COREDUMP_UART_END = b'================= CORE DUMP END ================='
    COREDUMP_UART_REGEX = re.compile(COREDUMP_UART_START + b'(.+?)' + COREDUMP_UART_END, re.DOTALL)

    # panic handler related messages
    PANIC_START = b'register dump:'
    PANIC_END = b'ELF file SHA256:'

    app: IdfApp
    serial: EspSerial

    def __init__(
        self,
        app: IdfApp,
        skip_check_coredump: bool = False,
        panic_output_decode_script: str | None = None,
        **kwargs,
    ) -> None:
        self.target = app.target
        self.skip_check_coredump = skip_check_coredump
        self._panic_output_decode_script = panic_output_decode_script

        super().__init__(app=app, **kwargs)

        self._hard_reset_func = self.serial.hard_reset

    @property
    def toolchain_prefix(self) -> str:
        """
        Returns:
            Toolchain prefix according to the `self.target`
        """
        if self.app.is_xtensa:
            return f'xtensa-{self.target}-elf-'
        elif self.app.is_riscv32:
            return 'riscv32-esp-elf-'
        else:
            raise ValueError(f'Unknown target: {self.target}')

    @property
    def panic_output_decode_script(self) -> str | None:
        """
        Returns:
            Panic output decode script path
        """

        script_filepath = self._panic_output_decode_script
        if not script_filepath or not os.path.isfile(script_filepath):
            module = importlib.util.find_spec('esp_idf_panic_decoder.gdb_panic_server')
            if not module:
                raise ValueError(
                    'Panic output decode script not found. '
                    'Please use the --panic-output-decode-script flag to provide a script '
                    'or install esp-idf-panic-decoder using the command: `pip install esp-idf-panic-decoder` .'
                )
            script_filepath = module.origin

        return os.path.realpath(script_filepath)

    def _get_prefix_map_path(self) -> str:
        primary = os.path.join(self.app.binary_path, 'gdbinit', 'prefix_map')
        fallback = os.path.join(self.app.binary_path, 'prefix_map_gdbinit')

        if os.path.exists(primary):
            return primary
        return fallback

    def _check_panic_decode_trigger(self):  # type: () -> None
        if not self.app.elf_file:
            logging.warning('No elf file found. Skipping decode panic output...')
            return

        with open(self.logfile, 'rb') as output_file:
            output = output_file.read()
        # get the panic output by looking for the indexes
        # of the first occurrences of PANIC_START and PANIC_END patterns
        panic_output_idx_start = output.find(self.PANIC_START) - 10
        panic_output_idx_end = output.find(self.PANIC_END, output.find(self.PANIC_START) + 1) + 15
        panic_output_res = output[panic_output_idx_start:panic_output_idx_end]
        panic_output = panic_output_res if panic_output_res else None
        if panic_output is None:
            return

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as panic_output_file:
            panic_output_file.write(panic_output)
            panic_output_file.flush()
        try:
            cmd = [
                f'{self.toolchain_prefix}-gdb',
                '--command',
                self._get_prefix_map_path(),
                '--batch',
                '-n',
                self.app.elf_file,
                '-ex',
                f'target remote | "{sys.executable}" "{self.panic_output_decode_script}" --target {self.target} "{panic_output_file.name}"',  # noqa: E501
                '-ex',
                'bt',
            ]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            logging.info('\n\nBacktrace:\n')
            logging.info(output.decode())
        except subprocess.CalledProcessError as e:
            logging.debug(f'Failed to run gdb_panic_server.py script: {e}\n{e.output}\n\n')
            logging.info(panic_output.decode())
        finally:
            if panic_output_file is not None:
                try:
                    os.unlink(panic_output_file.name)
                except OSError as e:
                    logging.debug(f"Couldn't remove temporary panic output file ({e})")

    def _check_coredump(self) -> None:
        """
        Handle errors by panic_handler_script or check core dumps via UART or partition table.
        Write the decoded or read core dumps into separated files.

        For UART and panic output, would read the `_pexpect_logfile` file.
        For partition, would read the flash according to the partition table. needs a valid `parttool_path`.

        Note:
            - May include multiple core dumps, since each test case may include several unity test cases.
            - May have duplicated core dumps, since after the core dump happened, the target chip would reboot
            automatically.

        Returns:
            None
        """
        if self.target in self.RISCV32_TARGETS:
            self._check_panic_decode_trigger()  # need IDF_PATH
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

        with open(self.logfile, 'rb') as fr:
            s = fr.read()

            for i, coredump in enumerate(set(self.COREDUMP_UART_REGEX.findall(s))):  # may duplicate
                coredump_file = None
                try:
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as coredump_file:
                        coredump_file.write(coredump.strip().replace(b'\r', b''))
                        coredump_file.flush()

                    coredump = CoreDump(
                        chip=self.target,
                        core=coredump_file.name,
                        core_format='b64',
                        prog=self.app.elf_file,
                    )
                    with open(os.path.join(self._meta.logdir, f'coredump_output_{i}'), 'w') as fw:
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
            raise ValueError('Invalid coredump format. Use _parse_b64_coredump for UART')

        with self.serial.disable_redirect_thread():
            coredump = CoreDump(
                chip=self.target,
                core_format=core_format,
                port=self.serial.port,
                prog=self.app.elf_file,
            )
            with open(os.path.join(self._meta.logdir, 'coredump_output'), 'w') as fw:
                with redirect_stdout(fw):
                    coredump.info_corefile()

    def close(self) -> None:
        if not self.skip_check_coredump:
            try:
                self._check_coredump()
            except Exception as e:
                logging.debug(e)
        super().close()

    def write(self, data: t.AnyStr) -> None:
        data_str = to_str(data).strip('\n') or ''
        if data_str == '*':
            warnings.warn(
                'if you\'re using `dut.expect_exact("Press ENTER to see the list of tests"); '
                'dut.write("*"); dut.expect_unity_test_output()` to run esp-idf unity tests, '
                'please consider using `dut.run_all_single_board_cases()` instead. '
                'It could help record the duration time and the error messages even for crashed test cases.',
                UserHint,
            )

        if data_str and data_str[0] == '[' and data_str[-1] == ']':
            group_name = data_str[1:-1]
            warnings.warn(
                f'if you\'re using `dut.expect_exact("Press ENTER to see the list of tests"); '
                f'dut.write("{data_str}"); dut.expect_unity_test_output()` to run esp-idf unity tests, '
                f'please consider using `dut.run_all_single_board_cases(group="{group_name}")` instead. '
                f'It could help record the duration time and the error messages even for crashed test cases.',
                UserHint,
            )

        super().write(data)

    ################
    # JTAG related #
    ################
    def setup_jtag(self):
        super().setup_jtag()
        if self.gdb:
            self.gdb.write(f'file {self.app.elf_file}')

        run_flash = True
        if self._meta and self._meta.hit_port_app_cache(self.serial.port, self.app):
            run_flash = False

        if run_flash:
            self.flash_via_jtag()

    def flash_via_jtag(self):
        if not self.openocd:
            logging.debug("no openocd instance created. can't flash via openocd `program_esp`")
            return

        if self.app.is_loadable_elf:
            # loadable elf flash to ram. no cache.
            # load via test script.
            # For example:
            # >>> self.gdb.write('mon reset halt')
            # >>> self.gdb.write('thb *0x40007d54')
            # >>> self.gdb.write('c')
            # >>> self.gdb.write('load')
            return

        for _f in self.app.flash_files:
            if _f.encrypted:
                raise ValueError("Encrypted files can't be flashed in via JTAG")
            self.openocd.write(f'program_esp {_f.file_path} {hex(_f.offset)} verify')

        if self._meta:
            self._meta.set_port_app_cache(self.serial.port, self.app)
