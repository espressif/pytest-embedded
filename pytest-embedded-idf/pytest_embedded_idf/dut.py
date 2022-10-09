import logging
import os
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pytest_embedded_serial.dut import SerialDut

from .app import IdfApp


@dataclass
class UnittestMenuCase:
    """
    Dataclass of esp-idf unit test cases parsed from test menu

    Attributes:
        index: The index of the case, which can be used to run this case.
        name: The name of the case.
        type: Type of this case, which can be `normal` `multi_stage` or `multi_device`.
        keywords: List of additional keywords of this case. For now, we have `disable` and `ignored`.
        groups: List of groups of this case, this is usually the component which this case belongs to.
        attributes: Dict of attributes of this case, which is used to describe timeout duration,
            test environment, etc.
        subcases: List of dict of subcases of this case, if this case is a `multi_stage` or `multi_device` one.
    """

    index: int
    name: str
    type: str
    keywords: List[str]
    groups: List[str]
    attributes: Dict[str, Any]
    subcases: List[Dict[str, Any]]


class IdfDut(SerialDut):
    """
    Dut class for serial ports connect to Espressif boards which are flashed with ESP-IDF apps

    Attributes:
        target (str): target chip type
        skip_check_coredump (bool): skip check core dumped or not while dut teardown if set to True
    """

    XTENSA_TARGETS = ['esp32', 'esp32s2', 'esp32s3']
    RISCV32_TARGETS = ['esp32c3', 'esp32h2', 'esp32c2']

    COREDUMP_UART_START = b'================= CORE DUMP START ================='
    COREDUMP_UART_END = b'================= CORE DUMP END ================='
    COREDUMP_UART_REGEX = re.compile(COREDUMP_UART_START + b'(.+?)' + COREDUMP_UART_END, re.DOTALL)

    # panic handler related messages
    PANIC_START = b'register dump:'
    PANIC_END = b'ELF file SHA256:'

    app: IdfApp

    def __init__(
        self,
        app: IdfApp,
        skip_check_coredump: bool = False,
        panic_output_decode_script: str = None,
        **kwargs,
    ) -> None:
        self.target = app.target
        self.skip_check_coredump = skip_check_coredump
        self._panic_output_decode_script = panic_output_decode_script

        super().__init__(app=app, **kwargs)

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

    @property
    def panic_output_decode_script(self) -> Optional[str]:
        """
        Returns:
            Panic output decode script path
        """
        script_filepath = self._panic_output_decode_script or os.path.join(
            os.getenv('IDF_PATH', 'IDF_PATH'),
            'tools',
            'gdb_panic_server.py',
        )
        if not os.path.isfile(script_filepath):
            raise ValueError(
                'Panic output decode script not found. Please use --panic-output-decode-script flag '
                'to provide script or set IDF_PATH (Default: $IDF_PATH/tools/gdb_panic_server.py)'
            )
        return os.path.realpath(script_filepath)

    def _check_panic_decode_trigger(self):  # type: () -> None
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
        toolchain_common = self.toolchain_prefix.replace(self.target, 'esp') + 'gdb'
        try:
            cmd = [
                toolchain_common,
                '--command',
                f'{self.app.app_path}/build/prefix_map_gdbinit',
                '--batch',
                '-n',
                self.app.elf_file,
                '-ex',
                "target remote | \"{python}\" \"{script}\" --target {target} \"{output_file}\"".format(
                    python=sys.executable,
                    script=self.panic_output_decode_script,
                    target=self.target,
                    output_file=panic_output_file.name,
                ),
                '-ex',
                'bt',
            ]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            logging.info('\n\nBacktrace:\n')
            logging.info(output.decode())  # noqa: E999
        except subprocess.CalledProcessError as e:
            logging.debug(f'Failed to run gdb_panic_server.py script: {e}\n{e.output}\n\n')
            logging.info(panic_output.decode())
        finally:
            if panic_output_file is not None:
                try:
                    os.unlink(panic_output_file.name)
                except OSError as e:
                    logging.debug(f'Couldn\'t remove temporary panic output file ({e})')

    def _check_coredump(self) -> None:
        """
        Handle errors by panic_handler_script or check core dumps via UART or partition table.
        Write the decoded or read core dumps into separated files.

        For UART and panic output, would read the `_pexpect_logfile` file.
        For partition, would read the flash according to the partition table. needs a valid `parttool_path`.

        Notes:
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
            raise ValueError(f'Invalid coredump format. Use _parse_b64_coredump for UART')

        with self.serial.disable_redirect_serial():
            coredump = CoreDump(
                chip=self.target,
                core_format=core_format,
                port=self.serial.port,
                prog=self.app.elf_file,
            )
            with open(os.path.join(self._meta.logdir, f'coredump_output'), 'w') as fw:
                with redirect_stdout(fw):
                    coredump.info_corefile()

    def close(self) -> None:
        if not self.skip_check_coredump:
            try:
                self._check_coredump()
            except ValueError as e:
                logging.debug(e)
        super().close()

    def parse_test_menu(
        self,
        ready_line: str = 'Press ENTER to see the list of tests',
        pattern="Here's the test menu, pick your combo:(.+)Enter test for running.",
        trigger: str = '',
    ) -> List[UnittestMenuCase]:
        """
        Get test case list from test menu via UART print.

        Args:
            ready_line: Prompt to indicate that device is ready to print test menu.
            pattern: Pattern to match the output from device, menu block should be in the first group.
                     This will be directly passed to `pexpect.expect()`.
            trigger: Keys to trigger device to print test menu by UART.

        Returns:
            A `list` of `UnittestMenuCase`, which includes info for each test case.
        """
        self.expect_exact(ready_line)
        self.write(trigger)
        menu_block = self.expect(pattern).group(1)
        s = str(menu_block, encoding='UTF-8')
        return self.parse_unity_menu_from_str(s)

    @staticmethod
    def parse_unity_menu_from_str(s: str) -> List[UnittestMenuCase]:
        """
        Parse test case mcnu from string to list of `UnittestMenuCase`.

        Args:
            s: string include test case menu.

        Returns:
            A `list` of `UnittestMenuCase`, which includes info for each test case.
        """
        print(s)
        cases = s.splitlines()

        case_regex = re.compile(r'\((\d+)\)\s\"(.+)\"\s(\[.+\])+')
        subcase_regex = re.compile(r'\t\((\d+)\)\s\"(.+)\"')

        test_menu = []
        for case in cases:
            case_match = case_regex.match(case)
            if case_match is not None:
                index, name, tag_block = case_match.groups()
                tags = re.findall(r'\[(.+?)\]', tag_block)

                if 'multi_stage' in tags:
                    _type = 'multi_stage'
                    tags.remove('multi_stage')
                elif 'multi_device' in tags:
                    _type = 'multi_device'
                    tags.remove('multi_device')
                else:
                    _type = 'normal'

                keyword = []
                if 'ignore' in tags:
                    keyword.append('ignore')
                    tags.remove('ignore')
                elif 'disable' in tags:
                    keyword = 'disable'
                    tags.remove('disable')

                attributes = {}
                group = []
                for tag in tags:
                    if '=' in tag:
                        k, v = tag.replace(' ', '').split('=')
                        attributes[k] = v
                    else:
                        group.append(tag)

                test_menu.append(
                    UnittestMenuCase(
                        index=int(index),
                        name=name,
                        type=_type,
                        keywords=keyword,
                        groups=group,
                        attributes=attributes,
                        subcases=[],
                    )
                )
                continue
            subcase_match = subcase_regex.match(case)
            if subcase_match is not None:
                index, name = subcase_match.groups()
                test_menu[-1].subcases.append({'index': int(index), 'name': name})
                continue

            if case != '':
                raise NotImplementedError('Unrecognized test case:', case)

        return test_menu

    def setup_jtag(self):
        super().setup_jtag()
        self.gdb.write(f'file {self.app.elf_file}')

        run_flash = True
        if self.serial.port in self._meta.port_app_cache:
            if self.app.binary_path == self._meta.port_app_cache[self.serial.port]:  # hit the cache
                logging.debug('hit port-app cache: %s - %s', self.serial.port, self.app.binary_path)
                logging.info('App is the same according to the session cache')
                run_flash = False

        if run_flash:
            self.flash_via_jtag()

    def flash_via_jtag(self):
        if self.app.is_loadable_elf:
            # loadable elf flash to ram. no cache.
            # load via test script.
            # For example:
            # self.gdb.write('mon reset halt')
            # self.gdb.write('thb *0x40007d54')
            # self.gdb.write('c')
            # self.gdb.write('load')
            return

        for _f in self.app.flash_files:
            if _f.encrypted:
                raise ValueError('Encrypted files can\'t be flashed in via JTAG')
            self.openocd.write(f'program_esp {_f.file_path} {hex(_f.offset)} verify')
            self.expect_exact('** Verify OK **')

        logging.debug('set port-app cache: %s - %s', self.serial.port, self.app.binary_path)
        self._meta.port_app_cache[self.serial.port] = self.app.binary_path
