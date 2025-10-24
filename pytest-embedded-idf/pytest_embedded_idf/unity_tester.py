# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import re
import time
import typing as t
import warnings
from collections import namedtuple
from collections.abc import Iterable
from dataclasses import dataclass

import pexpect
from pexpect.exceptions import TIMEOUT
from pytest_embedded.unity import (
    UNITY_BASIC_REGEX,
    UNITY_FIXTURE_REGEX,
    UNITY_SUMMARY_LINE_REGEX,
    TestCase,
    TestSuite,
)
from pytest_embedded.utils import remove_asci_color_code

if t.TYPE_CHECKING:
    from .dut import IdfDut

DEFAULT_START_RETRY = 3
DEFAULT_TIMEOUT = 90
WAIT_FOR_MENU_TIMEOUT = 10

READY_PATTERN_LIST = [
    'Press ENTER to see the list of tests',
    'Enter test for running',
    "Enter next test, or 'enter' to see menu",
]

_PRE_RUN_FAILURE_STR = '_PRE_RUN_FAILURE'


def _parse_unity_test_output(log: t.Optional[t.AnyStr], case_name: str, buffer_debug_str: str) -> t.Dict:
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
        logging.warning(
            'unity test case not found, probably due to a timeout. Assume the current test case is "%s"',
            case_name,
        )
        attrs = {
            'name': case_name,
            'result': 'FAIL',
            'message': buffer_debug_str or 'timeout',
        }
    elif len(res) == 1:
        attrs = {k: v for k, v in res[0].groupdict().items() if v is not None}
    else:
        warnings.warn('This function is for recording single unity test case only. Use the last matched one')
        attrs = {k: v for k, v in res[-1].groupdict().items() if v is not None}

    if log:
        attrs.update({'stdout': log})

    return attrs


def _add_test_case_to_test_suite(test_suite: TestSuite, attrs: t.Dict) -> None:
    """
    Add a test case to the test suite.

    :param test_suite: The test suite to add the test case to.
    :param attrs: The attributes of the test case.
    """
    testcase = TestCase(**attrs)
    test_suite.testcases.append(testcase)
    if testcase.result == 'FAIL':
        test_suite.attrs['failures'] += 1
    elif testcase.result == 'IGNORE':
        test_suite.attrs['skipped'] += 1
    else:
        test_suite.attrs['tests'] += 1


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

        self._ignore_first_ready_pattern = False

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

    def _hard_reset(self) -> None:
        if self._hard_reset_func:
            try:
                self._hard_reset_func()
            except NotImplementedError:
                # since menu printed but been expected (buffer has gone)... ignore the first ready pattern
                self.confirm_write('\n', expect_pattern=READY_PATTERN_LIST)
                self._ignore_first_ready_pattern = True
                pass

    def _get_ready(self, timeout: float = 30) -> None:
        if self._ignore_first_ready_pattern:
            self._ignore_first_ready_pattern = False
        else:
            self.expect_exact(READY_PATTERN_LIST, timeout=timeout)

    @property
    def test_menu(self) -> t.List[UnittestMenuCase]:
        if self._test_menu is None:
            self._test_menu = self._parse_test_menu()
            logging.debug('Successfully parsed unity test menu')
            self._hard_reset()

        return self._test_menu

    def _add_test_case_to_suite(self, attrs: t.Dict):
        _add_test_case_to_test_suite(self.testsuite, attrs)

    def _analyze_test_case_result(
        self,
        case: UnittestMenuCase,
        pre_run_failure: t.Optional[Exception],
        *,
        start_time: float = 0,
        timeout: float = 30,
    ):
        # if the pre_run_failure is not None, then the test case is skipped, since the error happens before
        if pre_run_failure:
            attrs = {
                'name': case.name,
                'result': 'IGNORE',
                'message': f'Skipped due to a failure before test execution. '
                f'The write command probably failed: {pre_run_failure}',
                'time': 0,
                'app_path': self.app.app_path,
            }
            self._add_test_case_to_suite(attrs)
            return

        log = ''
        try:
            remaining_timeout = timeout - (time.perf_counter() - start_time)
            if remaining_timeout < 0:  # pexpect process would expect 30s if < 0
                remaining_timeout = 0
            self.expect(UNITY_SUMMARY_LINE_REGEX, timeout=remaining_timeout)
        except Exception:  # result block missing
            pass
        else:  # result block exists
            log = remove_asci_color_code(self.pexpect_proc.before)
        finally:
            attrs = _parse_unity_test_output(log, case.name, self.pexpect_proc.buffer_debug_str)
            attrs.update(
                {
                    'app_path': self.app.app_path,
                    'time': round(time.perf_counter() - start_time, 3),
                }
            )

            self._add_test_case_to_suite(attrs)

    def _run_normal_case(
        self,
        case: UnittestMenuCase,
        *,
        reset: bool = False,
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

        try:
            if reset:
                self._hard_reset()

            _start_at = time.perf_counter()
            self._get_ready(timeout)
            self.confirm_write(case.index, expect_str=f'Running {case.name}...')
        except Exception as e:
            self._analyze_test_case_result(case, e)
        else:
            self._analyze_test_case_result(case, None, start_time=_start_at, timeout=timeout)

    def _run_multi_stage_case(
        self,
        case: UnittestMenuCase,
        *,
        reset: bool = False,
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

        try:
            if reset:
                self._hard_reset()

            _start_at = time.perf_counter()
            self._get_ready(timeout)
            self.confirm_write(case.index, expect_str=f'Running {case.name}...')
        except Exception as e:
            self._analyze_test_case_result(case, e)
        else:
            try:
                for sub_case in case.subcases:
                    if sub_case != case.subcases[0]:
                        self._get_ready(timeout)
                        self.confirm_write(case.index, expect_str=f'Running {case.name}...')

                    self.write(str(sub_case['index']))
            except Exception:
                # Any exception during the sub-case loop is a runtime failure.
                # We'll stop sending commands and let the result recorder handle the failure.
                pass
            finally:
                self._analyze_test_case_result(case, None, start_time=_start_at, timeout=timeout)

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

    @staticmethod
    def _select_to_run(group, name, attributes, case_groups, case_name, case_attributes):
        def validate_group():
            for _or in group:
                for _and in _or:
                    invert = _and.startswith('!')
                    _and = _and.lstrip('!')
                    result = _and in case_groups
                    if invert:
                        result = not result
                    if not result:
                        break
                else:
                    return True

            return False

        if not group and not name and not attributes:
            return True
        if group and validate_group():
            return True
        if name and case_name in name:
            return True
        if attributes and all(case_attributes.get(k) == v for k, v in attributes.items()):
            return True

        return False

    def run_all_single_board_cases(
        self,
        group: t.Optional[t.Union[str, list]] = None,
        reset: bool = False,
        timeout: float = 30,
        run_ignore_cases: bool = False,
        name: t.Optional[t.Union[str, list]] = None,
        attributes: t.Optional[dict] = None,
        dry_run: bool = False,
    ) -> None:
        """
        Run all single board cases, including multi_stage cases, and normal cases

        Note:
             If a group, name, and attributes are used together,
             then if test case matches any of them, it will be selected.

        Args:
            group: test case group or a list of test case groups to run. Supports 'and' with '&'.
                Supports group inversion with '!'.
            reset: Whether to perform a hardware reset before running a test case.
            timeout: Timeout in seconds. (Default: 30 seconds)
            run_ignore_cases: Whether to run ignored test cases or not.
            name: test case name or a list of test case names to run.
            attributes: Dictionary of attributes to filter and run test cases.
            dry_run: If True, then just show a list of test case names without running them.
                (please set the logging level as INFO to see them)
        """
        if group is None:
            group = []
        if isinstance(group, str):
            group: t.List[str] = [group]
        group: t.List[t.List[str]] = [[_and.strip() for _and in _or.split('&')] for _or in group]

        if isinstance(name, str):
            name: t.List[str] = [name]

        for case in self.test_menu:
            selected = self._select_to_run(group, name, attributes, case.groups, case.name, case.attributes)
            if not selected:
                continue

            if not case.is_ignored or run_ignore_cases:
                if dry_run:
                    logging.info('[dry run] %s | %s', case.index, case.name)
                    continue
                if case.type == 'normal':
                    self._run_normal_case(case, reset=reset, timeout=timeout)
                elif case.type == 'multi_stage':
                    self._run_multi_stage_case(case, reset=reset, timeout=timeout)


class _MultiDevTestDut:
    """
    Dut control for multidevice test case
    """

    # The signal pattens come from 'test_utils.c'
    SEND_SIGNAL_PREFIX = 'Send signal: '
    WAIT_SIGNAL_PREFIX = 'Waiting for signal: '
    UNITY_SEND_SIGNAL_REGEX = SEND_SIGNAL_PREFIX + r'\[(.*?)\]!'
    UNITY_WAIT_SIGNAL_REGEX = WAIT_SIGNAL_PREFIX + r'\[(.*?)\]!'
    signal_pattern_list: t.ClassVar[t.List[str]] = [
        UNITY_SEND_SIGNAL_REGEX,  # The dut send a signal
        UNITY_WAIT_SIGNAL_REGEX,  # The dut is blocked and waiting for a signal
        UNITY_SUMMARY_LINE_REGEX,  # Means the case finished
    ]

    DevResponse = namedtuple('DevResponse', ['completed', 'data'])

    def __init__(
        self,
        dut,
        case,
        sub_case_index,
        shared_message_query,
        start_retry,
        wait_for_menu_timeout=WAIT_FOR_MENU_TIMEOUT,
        runtest_timeout=DEFAULT_TIMEOUT,
    ):
        self.dut = dut
        self.case = case
        self.sub_case_index = sub_case_index
        self.shared_message_query = shared_message_query
        self.dut_index = self.sub_case_index - 1
        self.start_retry = start_retry
        self.wait_for_menu_timeout = wait_for_menu_timeout
        self.runtest_timeout = runtest_timeout

        self.work = self.run_case()
        self.init_time = time.perf_counter()
        self.response: _MultiDevTestDut.DevResponse = _MultiDevTestDut.DevResponse(False, None)

    def __iter__(self):
        return self.work

    def __next__(self):
        if self.response.completed:
            return self.response
        else:
            try:
                next(self.__iter__())
            except StopIteration as e:
                self.response = _MultiDevTestDut.DevResponse(True, self.process_raw_report_data(e.value))
                self.work.close()
            except TIMEOUT as e:
                self.response = _MultiDevTestDut.DevResponse(True, self.process_raw_report_data(e))
                self.work.close()
        return self.response

    def close(self):
        self.work.close()

    def interrupt(self):
        if not self.response.completed:
            self.response = _MultiDevTestDut.DevResponse(
                True, self.process_raw_report_data('Some of the dut failed, so this dut was interrupted.')
            )
            self.work.close()

    def run_case(self):
        try:
            yield from self._expect_exact(READY_PATTERN_LIST, self.wait_for_menu_timeout)
            # yield version of confirm_write
            for retry in range(self.start_retry):
                self.dut.write(str(self.case.index))
                try:
                    yield from self._expect_exact(self.case.name, 1)
                    break
                except TIMEOUT as e:
                    if retry >= self.start_retry - 1:
                        raise e
        except Exception as e:
            return _PRE_RUN_FAILURE_STR, {
                'name': self.case.name,
                'result': _PRE_RUN_FAILURE_STR,
                'message': f'Skipped due to a failure before test execution. The write command probably failed: {e}',
                'time': 0,
            }

        self.dut.write(str(self.sub_case_index))

        _start_time = time.perf_counter()
        while True:
            _current = time.perf_counter()
            _timeout = _start_time + self.runtest_timeout - _current

            if _timeout < 0:
                raise TIMEOUT('Tasks timed out, without other exception')

            pat = yield from self._expect(self.signal_pattern_list, _timeout)

            if pat is not None:
                match_str = pat.group().decode('utf-8')

                # Send a signal
                if self.SEND_SIGNAL_PREFIX in match_str:
                    send_sig = pat.group(1).decode('utf-8')

                    sig_name, sig_data = send_sig, ''
                    matched = re.search(r'(.*)\]\[(.*)', send_sig)
                    if matched:
                        sig_name, sig_data = matched.group(1), matched.group(2)

                    for i, q in enumerate(self.shared_message_query):
                        if i != self.dut_index:
                            q.append((sig_name, sig_data))

                # Waiting for a signal
                elif self.WAIT_SIGNAL_PREFIX in match_str:
                    wait_sig = pat.group(1).decode('utf-8')
                    while True:
                        yield

                        for i, (sig_name, sig_data) in enumerate(self.shared_message_query[self.dut_index]):
                            if wait_sig == sig_name:
                                break
                        else:
                            # Keep waiting the signal
                            if _start_time + self.runtest_timeout < time.perf_counter():
                                raise TIMEOUT(f'Not receive signal {wait_sig!r}')
                            continue

                        self.shared_message_query[self.dut_index].remove((sig_name, sig_data))
                        self.dut.write(sig_data)
                        break

                # Case finished
                elif 'Tests' in match_str:
                    case_duration = time.perf_counter() - _start_time
                    additional_attrs = {'time': round(case_duration, 3)}
                    log = remove_asci_color_code(self.dut.pexpect_proc.before)
                    return log, additional_attrs

    def _expect_exact(self, pattern, timeout):
        start = time.perf_counter()
        while True:
            try:
                yield 'Await for result'
                res = self.dut.expect_exact(pattern, timeout=0.01)
                return res
            except TIMEOUT as e:
                if time.perf_counter() - start > timeout:
                    raise e

    def _expect(self, pattern, timeout):
        start = time.perf_counter()
        while True:
            try:
                yield 'Await for result'
                res = self.dut.expect(pattern, timeout=0.01)
                return res
            except TIMEOUT as e:
                if time.perf_counter() - start > timeout:
                    raise e

    def process_raw_report_data(self, raw_data_to_report) -> t.Dict:
        additional_attrs = {}
        if isinstance(raw_data_to_report, tuple) and len(raw_data_to_report) == 2:
            log = str(raw_data_to_report[0])
            additional_attrs = raw_data_to_report[1]

            if log == _PRE_RUN_FAILURE_STR:
                return additional_attrs
        else:
            log = str(raw_data_to_report)

        attrs = _parse_unity_test_output(log, self.case.name, self.dut.pexpect_proc.buffer_debug_str)

        if additional_attrs:
            attrs.update(additional_attrs)

        attrs.update({'app_path': self.dut.app.app_path})

        return attrs


class MultiDevRunTestManager:
    """
    Manager for control dut generator function
    """

    def __init__(self, duts, case, start_retry, wait_for_menu_timeout, runtest_timeout):
        self.case = case
        self.workers: t.List[_MultiDevTestDut] = []
        shared_query = [[] for _ in case.subcases]
        for sub_case in case.subcases:
            index: int
            if isinstance(sub_case['index'], str):
                index = int(sub_case['index'], 10)
            else:
                index = sub_case['index']

            self.workers.append(
                _MultiDevTestDut(
                    dut=duts[index - 1],
                    case=case,
                    sub_case_index=index,
                    shared_message_query=shared_query,
                    start_retry=start_retry,
                    wait_for_menu_timeout=wait_for_menu_timeout,
                    runtest_timeout=runtest_timeout,
                )
            )

    def next_for_all(self):
        res = []
        err = []
        for i, it in enumerate(self.workers):
            try:
                r = next(it)
                if r.completed:
                    res.append(r.data)
            except Exception as e:
                err.append(e)
        return res, err

    def gather(self):
        try:
            while True:
                res, er = self.next_for_all()
                if er:
                    raise Exception('There are Exception: ', er)
                if len(res) == len(self.workers):
                    return res

                if any(True for r in res if r['result'] == 'FAIL'):
                    for it in self.workers:
                        it.interrupt()
        finally:
            for _t in self.workers:
                _t.close()

    @staticmethod
    def get_merge_data(test_cases_attr: t.List[t.Dict]) -> t.Dict:
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
                    output[k] = [val]
                else:
                    output[k].append(val)

        for k, val in output.items():
            if k in ('file', 'line'):
                output[k] = val[0]
            elif k == 'app_path':
                output[k] = '|'.join(val)
            else:
                output[k] = '<------------------->\n'.join(val)

        output['time'] = time_attr
        output['name'] = ' <---> '.join(list(name_attr))

        if _PRE_RUN_FAILURE_STR in results:
            output['result'] = 'IGNORE'
        elif 'FAIL' in results:
            output['result'] = 'FAIL'
        elif 'IGNORE' in results:
            output['result'] = 'IGNORE'
        else:
            output['result'] = (results - {'FAIL', 'IGNORE'}).pop()

        return output


class CaseTester:
    """
    The Generic tester of all the types

    Attributes:
        dut (IdfDut): The first dut if there is more than one
        test_menu (t.List[UnittestMenuCase]): The list of the cases
    """

    def __init__(self, dut: t.Union['IdfDut', t.List['IdfDut']]) -> None:  # type: ignore
        """
        Create the object for every dut and put them into the group
        """
        if isinstance(dut, Iterable):
            self.is_multi_dut = True
            self.dut: t.List[IdfDut] = list(dut)
            self.first_dut = self.dut[0]
            self.test_menu = self.first_dut.test_menu
        else:
            self.is_multi_dut = False
            self.dut = [dut]
            self.first_dut = dut
            self.test_menu = self.dut[0].test_menu

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
            for dut in self.dut:
                dut.serial.hard_reset()

        mdm = MultiDevRunTestManager(
            duts=self.dut, case=case, start_retry=start_retry, wait_for_menu_timeout=timeout, runtest_timeout=timeout
        )
        data_to_report = mdm.gather()
        merged_data = mdm.get_merge_data(data_to_report)
        _add_test_case_to_test_suite(mdm.workers[0].dut.testsuite, merged_data)

    def run_normal_case(self, case: UnittestMenuCase, reset: bool = False, timeout: int = 90) -> None:
        """
        Run a specific normal case

        Notes:
            Will skip if the case type is not normal

        Args:
            case: the specific case that parsed in test menu
            reset: whether do a hardware reset before running the case
            timeout: timeout in second
        """
        self.first_dut._run_normal_case(case, reset=reset, timeout=timeout)

    def run_multi_stage_case(self, case: UnittestMenuCase, reset: bool = False, timeout: int = 90) -> None:
        """
        Run a specific multi_stage case

        Notes:
            Will skip if the case type is not multi_stage

        Args:
            case: the specific case that parsed in test menu
            reset: whether do a hardware reset before running the case
            timeout: timeout in second
        """
        self.first_dut._run_multi_stage_case(case, reset=reset, timeout=timeout)

    def run_all_normal_cases(self, reset: bool = False, timeout: int = 90) -> None:
        """
        Run all normal cases

        Args:
            reset: whether do a hardware reset before running the case
            timeout: timeout in second
        """
        for case in self.test_menu:
            self.run_normal_case(case, reset, timeout=timeout)

    def run_all_multi_stage_cases(self, reset: bool = False, timeout: int = 90) -> None:
        """
        Run all multi_stage cases

        Args:
            reset: whether do a hardware reset before running the case
            timeout: timeout in second
        """
        for case in self.test_menu:
            self.run_multi_stage_case(case, reset=reset, timeout=timeout)

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
            timeout: timeout in second, setup time excluded
            start_retry (int): number of retries for a single case when it is failed to start
        """

        if case.attributes.get('timeout'):
            timeout = int(case.attributes['timeout'])

        if case.type == 'normal':
            self.first_dut._run_normal_case(case, reset=reset, timeout=timeout)
        elif case.type == 'multi_stage':
            self.first_dut._run_multi_stage_case(case, reset=reset, timeout=timeout)
        elif case.type == 'multi_device':
            self.run_multi_dev_case(case, reset=reset, timeout=timeout, start_retry=start_retry)
