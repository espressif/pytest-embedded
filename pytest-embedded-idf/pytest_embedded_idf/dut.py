import logging
import os
import re
import tempfile
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Any, Dict, List

from pytest_embedded import PexpectProcess
from pytest_embedded_serial.dut import SerialDut

from .app import IdfApp
from .serial import IdfSerial


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
