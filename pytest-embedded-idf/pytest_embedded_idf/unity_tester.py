# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import functools
import logging
import re
import threading
import time
import typing as t
import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from threading import Thread

import pexpect
from pexpect.exceptions import TIMEOUT
from pytest_embedded.unity import (
    UNITY_BASIC_REGEX,
    UNITY_FIXTURE_REGEX,
    UNITY_SUMMARY_LINE_REGEX,
    TestCase,
)
from pytest_embedded.utils import remove_asci_color_code

if t.TYPE_CHECKING:
    from .dut import IdfDut

DEFAULT_START_RETRY = 3
DEFAULT_TIMEOUT = 90

READY_PATTERN_LIST = [
    'Press ENTER to see the list of tests',
    'Enter test for running',
    'Enter next test, or \'enter\' to see menu',
]


@dataclass
class UnittestMenuCase:
    """
    Dataclass of esp-idf unit test cases parsed from test menu
    """

    #: The index of the case, which can be used to run this case.
    index: int
    #: The name of the case.
    name: str
    #: Type of this case, which can be `normal` `multi_stage` or `multi_device`.
    type: str
    #: List of additional keywords of this case. For now, we have `disable` and `ignore`.
    keywords: t.List[str]
    #: List of groups of this case, this is usually the component which this case belongs to.
    groups: t.List[str]
    #: Dict of attributes of this case, which is used to describe timeout duration,
    attributes: t.Dict[str, t.Any]
    #: List of dict of subcases of this case, if this case is a `multi_stage` or `multi_device` one.
    subcases: t.List[t.Dict[str, t.Any]]

    @property
    def is_ignored(self):
        return 'ignore' in self.keywords or 'disable' in self.keywords


class IdfUnityDutMixin:
    """
    This mixin class provide ESP-IDF modified unity test framework related functions.
    """

    def __init__(self, *args, **kwargs):
        self._test_menu: t.List[UnittestMenuCase] = None  # type: ignore

        self._hard_reset_func: t.Optional[t.Callable] = None

        super().__init__(*args, **kwargs)

    def confirm_write(
        self,
        write_str: t.Any,
        *,
        expect_pattern: t.Any = None,
        expect_str: t.Any = None,
        timeout: int = 1,
        retry_times: int = 3,
    ):
        if not ((expect_pattern is None) ^ (expect_str is None)):
            raise ValueError('should provide expect_pattern= or expect_str=, but not both nor none')

        err = None
        for _ in range(retry_times):
            try:
                self.write(str(write_str))
                if expect_pattern is not None:
                    res = self.expect(expect_pattern, timeout=timeout)
                else:
                    res = self.expect_exact(expect_str, timeout=timeout)
            except pexpect.TIMEOUT as e:
                err = e
            else:
                break
        else:
            raise err

        return res

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
        res = self.confirm_write(trigger, expect_pattern=pattern)
        return self._parse_unity_menu_from_str(res.group(1).decode('utf8'))

    def parse_test_menu(
        self,
        ready_line: str = 'Press ENTER to see the list of tests',
        pattern="Here's the test menu, pick your combo:(.+)Enter test for running.",
        trigger: str = '',
    ) -> t.List[UnittestMenuCase]:
        warnings.warn(
            'Please use `dut.test_menu` property directly, '
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

        return IdfUnityDutMixin._parse_unity_menu_from_str(s)

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
            if self._hard_reset_func:
                try:
                    self._hard_reset_func()
                except NotImplementedError:
                    self.write('\n')  # print the menu

        return self._test_menu

    def _record_single_unity_test_case(func):
        """
        The first argument of the function that is using this decorator must be `case`. passing with args.

        Note:
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
                    if kwargs.pop('reset') and self._hard_reset_func:
                        try:
                            self._hard_reset_func()
                        except NotImplementedError:
                            self.write('\n')  # print the menu

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

        if log:
            attrs.update({'stdout': log})

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
        reset: bool = False,  # noqa
        timeout: float = 30,
    ) -> None:
        """
        Run a specific normal case

        Note:
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
        self.confirm_write(case.index, expect_str=f'Running {case.name}...')

    @_record_single_unity_test_case
    def _run_multi_stage_case(
        self,
        case: UnittestMenuCase,
        reset: bool = False,  # noqa
        timeout: float = 30,
    ) -> None:
        """
        Run a specific multi_stage case

        Note:
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
            self.confirm_write(case.index, expect_str=f'Running {case.name}...')

            # here we can't use confirm_write because the sub cases won't print anything
            self.write(str(sub_case['index']))

            _timestamp = time.perf_counter()

    def run_single_board_case(self, name: str, reset: bool = False, timeout: float = 30) -> None:
        for case in self.test_menu:
            if case.name == name and case.type == 'normal':
                self._run_normal_case(case, reset=reset, timeout=timeout)
                break
            elif case.name == name and case.type == 'multi_stage':
                self._run_multi_stage_case(case, reset=reset, timeout=timeout)
                break
        else:
            raise ValueError(f'single-board test case {name} not found')

    def run_all_single_board_cases(
        self,
        group: t.Optional[str] = None,
        reset: bool = False,
        timeout: float = 30,
        run_ignore_cases: bool = False,
    ) -> None:
        """
        Run all single board cases, including multi_stage cases, and normal cases

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


class ResourcesProxy:
    """
    Interface for share data between main thread and LoopedDevWorker thread

    Attributes:
        dut (IdfDut): Object of the Device under test
        group (List[MultiDevResource]): List of MultiDevResource, same instance for all ResourcesProxy
        recv_sig (t.List[str]): The list of received signals from other dut
    """

    def __init__(self, **kwargs):
        self.dut = kwargs['dut']
        self.group = kwargs['group']
        self.recv_sig: t.List[str] = []

        self.case = None
        self.sub_case_index = None
        self.start_retry = None
        self.start_time = None
        self.returned_value = None
        self.raw_data_to_report = None
        self.timeout = 0
        self.wait_for_menu_timeout = 0


class LoopedDevWorker:
    """
    Worker for processing received task from main thread through ResourcesProxy

    Attributes:
        worker (Thread): Thread for running loop task
        wait_for_task_event (Event): Event for lock worker before receive task
        task_complete_event (Event): Event for lock result processing before completed/failed task
        rp (ResourcesProxy): Interface for storing shared variables between main thread and worker
    """

    SEND_SIGNAL_PREFIX = 'Send signal: '
    WAIT_SIGNAL_PREFIX = 'Waiting for signal: '
    UNITY_SEND_SIGNAL_REGEX = SEND_SIGNAL_PREFIX + r'\[(.*?)\]!'
    UNITY_WAIT_SIGNAL_REGEX = WAIT_SIGNAL_PREFIX + r'\[(.*?)\]!'

    def __init__(
        self,
        worker: type(Thread),
        event: type(threading.Event),
        resource_proxy: ResourcesProxy,
    ):
        self.wait_for_task_event = event()
        self.task_complete_event = event()
        self.rp = resource_proxy

        def loop():
            while True:
                self.wait_for_task_event.wait()
                self.wait_for_task_event.clear()
                self.rp.dut.serial.hard_reset()

                self.rp.returned_value = None

                try:
                    self.rp.returned_value = self.run_case()
                except Exception as e:
                    self.rp.returned_value = e

                self.task_complete_event.set()

        self.worker = worker(target=loop, daemon=True)
        self.worker.start()

    def setup_task(self, case, sub_case_index, start_retry, timeout) -> None:
        self.rp.case = case
        self.rp.sub_case_index = sub_case_index
        self.rp.start_retry = start_retry
        self.rp.start_time = time.perf_counter()
        self.rp.wait_for_menu_timeout = timeout
        self.rp.timeout = timeout

    def start_task(self) -> None:
        self.wait_for_task_event.set()

    def wait_for_result(self) -> None:
        self.task_complete_event.wait()
        res: t.Tuple[str, t.Dict] | Exception = self.rp.returned_value
        self.task_complete_event.clear()
        self.rp.raw_data_to_report = res

    def process_raw_data_to_report(self) -> t.Dict:
        additional_attrs = {}
        if isinstance(self.rp.raw_data_to_report, tuple) and len(self.rp.raw_data_to_report) == 2:
            log = str(self.rp.raw_data_to_report[0])
            additional_attrs = self.rp.raw_data_to_report[1]
        else:
            log = str(self.rp.raw_data_to_report)

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
            logging.warning(f'unity test case not found, use case {self.rp.case.name} instead')
            attrs = {
                'name': self.rp.case.name,
                'result': 'FAIL',
                'message': self.rp.dut.pexpect_proc.buffer_debug_str,
                'time': self.rp.timeout,
            }
        elif len(res) == 1:
            attrs = {k: v for k, v in res[0].groupdict().items() if v is not None}
        else:
            warnings.warn('This function is for recording single unity test case only. Use the last matched one')
            attrs = {k: v for k, v in res[-1].groupdict().items() if v is not None}

        if additional_attrs:
            attrs.update(additional_attrs)

        if log:
            attrs.update({'stdout': log})

        return attrs

    @staticmethod
    def merge_result(test_cases_attr: t.List[t.Dict]) -> t.Dict:
        output = {}
        results = set()
        time_attr = 0.0
        name_attr = set()
        for ind, attr in enumerate(test_cases_attr):
            for k, val in attr.items():
                if k == 'result':
                    results.add(val)
                    continue
                if k == 'name':
                    name_attr.add(val)
                    continue
                if k == 'time':
                    time_attr = max(time_attr, float(val))
                    continue

                if k not in output:
                    output[k] = [f'[group dev-{ind}]: {val}']
                else:
                    output[k].append(f'[group dev-{ind}]: {val}')

        for k, val in output.items():
            output[k] = '<------------------->\n'.join(output[k])

        output['time'] = time_attr
        output['name'] = ' <---> '.join(list(name_attr))

        if 'FAIL' in results:
            output['result'] = 'FAIL'
        elif 'IGNORE' in results:
            output['result'] = 'IGNORE'
        else:
            output['result'] = (results - {'FAIL', 'IGNORE'}).pop()

        return output

    def add_to_report(self, attrs):
        testcase = TestCase(**attrs)
        self.rp.dut.testsuite.testcases.append(testcase)

        if testcase.result == 'FAIL':
            self.rp.dut.testsuite.attrs['failures'] += 1
        elif testcase.result == 'IGNORE':
            self.rp.dut.testsuite.attrs['skipped'] += 1
        else:
            self.rp.dut.testsuite.attrs['tests'] += 1

    def clear_var_values(self) -> None:
        self.rp.recv_sig.clear()
        self.rp.returned_value = None

    def run_case(self, **kwargs):
        """
        The thread target function
        Will run for each case on each dut

        Call the wrapped function to trigger the case
        Then keep listening on the dut for the signal

            - If the dut send a signal, it will be put into others' recv_sig
            - If the dut waits for a signal, it block and keep polling for the recv_sig until get the signal it requires
            - If the dut finished running the case, it will quite the loop and terminate the thread
        """
        signal_pattern_list = [
            self.UNITY_SEND_SIGNAL_REGEX,  # The dut send a signal
            self.UNITY_WAIT_SIGNAL_REGEX,  # The dut is blocked and waiting for a signal
            UNITY_SUMMARY_LINE_REGEX,  # Means the case finished
        ]

        # Start the case
        self.rp.dut.expect_exact(READY_PATTERN_LIST, timeout=self.rp.wait_for_menu_timeout)
        _start_time = time.perf_counter()

        # Retry at defined number of times if not write successfully
        for retry in range(self.rp.start_retry):
            self.rp.dut.write(str(self.rp.case.index))
            try:
                self.rp.dut.expect_exact(self.rp.case.name, timeout=1)
                break
            except TIMEOUT as e:
                if retry >= self.rp.start_retry - 1:
                    raise e

        self.rp.dut.write(str(self.rp.sub_case_index))

        # Wait for the specific patterns, only exist when the sub-case finished
        while True:
            _current = time.perf_counter()
            _timeout = _start_time + self.rp.timeout - _current
            if _timeout < 0:
                raise TIMEOUT('Tasks timed out, without other exception')

            pat = self.rp.dut.expect(signal_pattern_list, timeout=_timeout)
            if pat is not None:
                match_str = pat.group().decode('utf-8')

                # Send a signal
                if self.SEND_SIGNAL_PREFIX in match_str:
                    send_sig = pat.group(1).decode('utf-8')
                    for d in self.rp.group:
                        d.rp.recv_sig.append(send_sig)

                # Waiting for a signal
                elif self.WAIT_SIGNAL_PREFIX in match_str:
                    wait_sig = pat.group(1).decode('utf-8')
                    while True:
                        if wait_sig in self.rp.recv_sig:
                            self.rp.recv_sig.remove(wait_sig)
                            self.rp.dut.write('')
                            break
                        # Keep waiting the signal
                        else:
                            time.sleep(0.1)
                            if _start_time + self.rp.timeout < time.perf_counter():
                                raise TIMEOUT('Not receive signal %r' % wait_sig)

                # Case finished
                elif 'Tests' in match_str:
                    case_end_time = time.perf_counter()
                    case_duration = case_end_time - self.rp.start_time
                    additional_attrs = {'time': round(case_duration, 3)}
                    log = remove_asci_color_code(self.rp.dut.pexpect_proc.before)
                    return log, additional_attrs


class MultiDevResource:
    """
    Resources of multi_dev dut

    Attributes:
        rp (ResourcesProxy): Interface for storing shared variables between main thread and "worker"
        worker (LoopedDevWorker): Worker for processing received task from main thread through ResourcesProxy
    """

    def __init__(self, dut: 'IdfDut', group: t.List['MultiDevResource']) -> None:
        self.rp = ResourcesProxy(dut=dut, group=group)

        self.worker = LoopedDevWorker(worker=Thread, event=threading.Event, resource_proxy=self.rp)


class CaseTester:
    """
    The Generic tester of all the types

    Attributes:
        group (t.List[MultiDevResource]): The group of the devices' resources
        dut (IdfDut): The first dut if there is more than one
        test_menu (t.List[UnittestMenuCase]): The list of the cases
    """

    # The signal pattens come from 'test_utils.c'
    SEND_SIGNAL_PREFIX = 'Send signal: '
    WAIT_SIGNAL_PREFIX = 'Waiting for signal: '
    UNITY_SEND_SIGNAL_REGEX = SEND_SIGNAL_PREFIX + r'\[(.*?)\]!'
    UNITY_WAIT_SIGNAL_REGEX = WAIT_SIGNAL_PREFIX + r'\[(.*?)\]!'

    def __init__(self, dut: t.Union['IdfDut', t.List['IdfDut']]) -> None:  # type: ignore
        """
        Create the object for every dut and put them into the group
        """
        if isinstance(dut, Iterable):
            self.is_multi_dut = True
            self.dut = list(dut)
            self.first_dut = self.dut[0]
            self.test_menu = self.first_dut.test_menu
        else:
            self.is_multi_dut = False
            self.dut = dut
            self.first_dut = dut
            self.test_menu = self.dut.test_menu

        if self.is_multi_dut:
            self.group: t.List[MultiDevResource] = []
            if isinstance(dut, list):
                for item in dut:
                    dev_res = MultiDevResource(item, self.group)
                    self.group.append(dev_res)

    def run_multi_dev_case(
        self,
        case: UnittestMenuCase,
        reset: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        start_retry: int = DEFAULT_START_RETRY,
    ) -> None:
        """
        Run a specific multi_device case

        Note:
            Will skip with a warning if the case type is not multi_device

        Args:
            case: the specific case that parsed in test menu
            reset: whether to perform a hardware reset before running a case
            timeout: timeout in second
            start_retry (int): number of retries for a single case when it is failed to start
        """
        if case.type != 'multi_device':
            logging.warning('case %s is not a multi device case', case.name)
            return

        if not self.is_multi_dut:
            logging.warning(
                'multi-device mode is not activated. Please refer to '
                'https://docs.espressif.com/projects/pytest-embedded/en/latest/key_concepts/#multi-duts '
                'for detailed documents'
            )
            return

        if reset:
            for dev_res in self.group:
                dev_res.rp.dut.serial.hard_reset()

        tasks = []
        for sub_case in case.subcases:
            if isinstance(sub_case['index'], str):
                index = int(sub_case['index'], 10)
            else:
                index = sub_case['index']
            tasks.append(index)

        for i, task in enumerate(tasks):
            self.group[i].worker.setup_task(case=case, sub_case_index=task, start_retry=start_retry, timeout=timeout)

        for i, task in enumerate(tasks):
            self.group[i].worker.start_task()
        for i, task in enumerate(tasks):
            self.group[i].worker.wait_for_result()

        data_to_report_list = [self.group[i].worker.process_raw_data_to_report() for i, task in enumerate(tasks)]
        merged_data = self.group[0].worker.merge_result(data_to_report_list)
        self.group[0].worker.add_to_report(merged_data)

        for i, task in enumerate(tasks):
            self.group[i].worker.clear_var_values()

    def run_all_multi_dev_cases(
        self,
        reset: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        start_retry: int = DEFAULT_START_RETRY,
    ) -> None:
        """
        Run only multi_device cases

        Args:
            reset: whether to perform a hardware reset before running a case
            timeout: timeout in second
            start_retry (int): number of retries for a single case when it is failed to start
        """
        for case in self.test_menu:
            # Run multi_device case on every device
            self.run_multi_dev_case(case, reset, timeout, start_retry)

    def run_all_cases(
        self,
        reset: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
        start_retry: int = DEFAULT_START_RETRY,
    ) -> None:
        """
        Run all cases

        Args:
            reset: whether to perform a hardware reset before running a case
            timeout: timeout in second
            start_retry (int): number of retries for a single case when it is failed to start
        """
        for case in self.test_menu:
            self.run_case(case, reset, timeout=timeout, start_retry=start_retry)

    def run_case(
        self,
        case: UnittestMenuCase,
        reset: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
        start_retry: int = DEFAULT_START_RETRY,
    ) -> None:
        """
        Run a specific case

        Args:
            case: the specific case that parsed in test menu
            reset: whether to perform a hardware reset before running a case
            timeout: timeout in second
            start_retry (int): number of retries for a single case when it is failed to start
        """
        warnings.warn(
            'Current timeout logic not clear: currently it is a sum of wait board menu time and runtest time.'
            'Will be renamed and split into two time in future',
            DeprecationWarning,
        )

        if case.attributes.get('timeout'):
            timeout = int(case.attributes['timeout'])

        if case.type == 'normal':
            self.first_dut._run_normal_case(case, reset=reset, timeout=timeout)
        elif case.type == 'multi_stage':
            self.first_dut._run_multi_stage_case(case, reset=reset, timeout=timeout)
        elif case.type == 'multi_device':
            self.run_multi_dev_case(case, reset=reset, timeout=timeout, start_retry=start_retry)
