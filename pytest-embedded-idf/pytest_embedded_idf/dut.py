import functools
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import typing as t
import warnings
from contextlib import redirect_stdout

from pytest_embedded.unity import (
    UNITY_BASIC_REGEX,
    UNITY_FIXTURE_REGEX,
    UNITY_SUMMARY_LINE_REGEX,
    TestCase,
)
from pytest_embedded.utils import UserHint, remove_asci_color_code, to_str
from pytest_embedded_serial.dut import SerialDut

from .app import IdfApp
from .unity_tester import READY_PATTERN_LIST, UnittestMenuCase


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
        self._test_menu: t.List[UnittestMenuCase] = None  # type: ignore

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
            return f'riscv32-esp-elf-'
        else:
            raise ValueError(f'Unknown target: {self.target}')

    @property
    def panic_output_decode_script(self) -> t.Optional[str]:
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
        try:
            cmd = [
                f'{self.toolchain_prefix}-gdb',
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
            except ValueError as e:
                logging.debug(e)
        super().close()

    #####################
    # IDF-unity related #
    #####################
    def _parse_test_menu(
        self,
        ready_line: str = 'Press ENTER to see the list of tests',
        pattern="Here's the test menu, pick your combo:(.+)Enter test for running.",
        trigger: str = '',
    ) -> t.List[UnittestMenuCase]:
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
        return self._parse_unity_menu_from_str(s)

    def parse_test_menu(
        self,
        ready_line: str = 'Press ENTER to see the list of tests',
        pattern="Here's the test menu, pick your combo:(.+)Enter test for running.",
        trigger: str = '',
    ) -> t.List[UnittestMenuCase]:
        warnings.warn(
            'Use `dut.test_menu` property directly, '
            'will rename this function to `_parse_test_menu` in release 2.0.0',
            DeprecationWarning,
        )

        return self._parse_test_menu(ready_line, pattern, trigger)

    @staticmethod
    def parse_unity_menu_from_str(s: str) -> t.List[UnittestMenuCase]:
        warnings.warn(
            'Please use `dut.test_menu` property directly, '
            'will rename this function to `_parse_unity_menu_from_str` in release 2.0.0',
            DeprecationWarning,
        )

        return IdfDut._parse_unity_menu_from_str(s)

    @staticmethod
    def _parse_unity_menu_from_str(s: str) -> t.List[UnittestMenuCase]:
        """
        Parse test case menu from string to list of `UnittestMenuCase`.

        Args:
            s: string include test case menu.

        Returns:
            A `list` of `UnittestMenuCase`, which includes info for each test case.
        """
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

    @property
    def test_menu(self) -> t.List[UnittestMenuCase]:
        if self._test_menu is None:
            self._test_menu = self._parse_test_menu()
            logging.debug('Successfully parsed unity test menu')
            self.serial.hard_reset()

        return self._test_menu

    def _record_single_unity_test_case(func):
        """
        The first argument of the function that is using this decorator must be `case`. passing with args.

        Notes:
            This function is better than `dut.expect_unity_output()` since it will record the test case even it core
                dumped during running the test case or other reasons that cause the final result block is uncaught.
        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            _start_at = time.perf_counter()  # declare here in case hard reset failed
            _timeout = kwargs.get('timeout', 30)
            _case = args[0]

            try:
                # do it here since the first hard reset before test case shouldn't be counted in duration time
                if 'reset' in kwargs:
                    if kwargs.pop('reset'):
                        self.serial.hard_reset()

                _start_at = time.perf_counter()
                func(self, *args, **kwargs)
            finally:
                _timestamp = time.perf_counter()
                _log = ''
                try:
                    _timeout = _timeout - _timestamp + _start_at
                    if _timeout < 0:  # pexpect process would expect 30s if < 0
                        _timeout = 0
                    self.expect(UNITY_SUMMARY_LINE_REGEX, timeout=_timeout)
                except Exception:  # result block missing # noqa
                    pass
                else:  # result block exists
                    _log = remove_asci_color_code(self.pexpect_proc.before)
                finally:
                    _end_at = time.perf_counter()
                    self._add_single_unity_test_case(
                        _case, _log, additional_attrs={'time': round(_end_at - _start_at, 3)}
                    )

        return wrapper

    def _add_single_unity_test_case(
        self, case: UnittestMenuCase, log: t.Optional[t.AnyStr], additional_attrs: t.Optional[t.Dict[str, t.Any]] = None
    ):
        if log:
            # check format
            check = UNITY_FIXTURE_REGEX.search(log)
            if check:
                regex = UNITY_FIXTURE_REGEX
            else:
                regex = UNITY_BASIC_REGEX

            res = list(regex.finditer(log))
        else:
            res = []

        # real parsing
        if len(res) == 0:
            logging.warning(f'unity test case not found, use case {case.name} instead')
            attrs = {'name': case.name, 'result': 'FAIL', 'message': self.pexpect_proc.buffer_debug_str}
        elif len(res) == 1:
            attrs = {k: v for k, v in res[0].groupdict().items() if v is not None}
        else:
            warnings.warn('This function is for recording single unity test case only. Use the last matched one')
            attrs = {k: v for k, v in res[-1].groupdict().items() if v is not None}

        if additional_attrs:
            attrs.update(additional_attrs)

        testcase = TestCase(**attrs)
        self.testsuite.testcases.append(testcase)
        if testcase.result == 'FAIL':
            self.testsuite.attrs['failures'] += 1
        elif testcase.result == 'IGNORE':
            self.testsuite.attrs['skipped'] += 1
        else:
            self.testsuite.attrs['tests'] += 1

    @_record_single_unity_test_case
    def _run_normal_case(
        self,
        case: UnittestMenuCase,
        reset: bool = False,
        timeout: float = 30,
    ) -> None:
        """
        Run a specific normal case

        Notes:
            Will skip with a warning if the case type is not "normal"

        Args:
            case: the specific case that parsed in test menu
            reset: whether to perform a hardware reset before running a case
            timeout: timeout. (Default: 30 seconds)
        """
        if case.type != 'normal':
            logging.warning('case %s is not a normal case', case.name)
            return

        self.expect_exact(READY_PATTERN_LIST, timeout=timeout)
        self.write(str(case.index))
        self.expect_exact(f'Running {case.name}...', timeout=1)

    @_record_single_unity_test_case
    def _run_multi_stage_case(
        self,
        case: UnittestMenuCase,
        reset: bool = False,
        timeout: float = 30,
    ) -> None:
        """
        Run a specific multi_stage case

        Notes:
            Will skip with a warning if the case type is not "multi_stage"

        Args:
            case: the specific case that parsed in test menu
            reset: whether to perform a hardware reset before running a case
            timeout: timeout. (Default: 30 seconds)
        """
        if case.type != 'multi_stage':
            logging.warning('case %s is not a multi stage case', case.name)
            return

        _start_at = time.perf_counter()
        _timestamp = _start_at
        for sub_case in case.subcases:
            _timeout = timeout - _timestamp + _start_at
            if _timeout < 0:  # pexpect process would expect 30s if < 0
                _timeout = 0
            self.expect_exact(READY_PATTERN_LIST, timeout=_timeout)
            self.write(str(case.index))
            self.expect_exact(case.name, timeout=1)
            self.write(str(sub_case['index']))
            _timestamp = time.perf_counter()

    def run_all_single_board_cases(
        self,
        group: t.Optional[str] = None,
        reset: bool = False,
        timeout: float = 30,
        run_ignore_cases: bool = False,
    ):
        """
        Run all multi_stage cases

        Args:
            group: test case group
            reset: whether to perform a hardware reset before running a case
            timeout: timeout. (Default: 30 seconds)
            run_ignore_cases: run ignored test cases or not
        """
        for case in self.test_menu:
            if not group or group in case.groups:
                if not case.is_ignored or run_ignore_cases:
                    if case.type == 'normal':
                        self._run_normal_case(case, reset=reset, timeout=timeout)
                    elif case.type == 'multi_stage':
                        self._run_multi_stage_case(case, reset=reset, timeout=timeout)

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
            logging.warning('no openocd instance created. can\'t flash via openocd `program_esp`')
            return

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

        if self._meta:
            self._meta.set_port_app_cache(self.serial.port, self.app)
