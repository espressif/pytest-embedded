# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import logging
import time
import typing as t
from collections.abc import Iterable
from dataclasses import dataclass
from threading import Semaphore, Thread

from pexpect.exceptions import TIMEOUT
from pytest_embedded import unity, utils

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

    Attributes:
        index: The index of the case, which can be used to run this case.
        name: The name of the case.
        type: Type of this case, which can be `normal` `multi_stage` or `multi_device`.
        keywords: List of additional keywords of this case. For now, we have `disable` and `ignore`.
        groups: List of groups of this case, this is usually the component which this case belongs to.
        attributes: Dict of attributes of this case, which is used to describe timeout duration,
            test environment, etc.
        subcases: List of dict of subcases of this case, if this case is a `multi_stage` or `multi_device` one.
    """

    index: int
    name: str
    type: str
    keywords: t.List[str]
    groups: t.List[str]
    attributes: t.Dict[str, t.Any]
    subcases: t.List[t.Dict[str, t.Any]]

    @property
    def is_ignored(self):
        return 'ignore' in self.keywords or 'disable' in self.keywords


class MultiDevResource:
    """
    Resources of multi_dev dut

    Attributes:
        dut (IdfDut): Object of the Device under test
        sem (Semaphore): Semaphore of monitoring whether the case finished
        recv_sig (t.List[str]): The list of received signals from other dut
        thread (Thread): The thread of monitoring the signals
    """

    def __init__(self, dut: 'IdfDut') -> None:
        self.dut = dut
        self.sem = Semaphore()
        self.recv_sig: t.List[str] = []
        self.thread: Thread = None  # type: ignore


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
                    dev_res = MultiDevResource(item)
                    self.group.append(dev_res)

    def _wait_multi_dev_case_finish(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """
        Wait until all the sub-cases of this multi_device case finished
        """
        for d in self.group:
            if d.sem.acquire(timeout=timeout):
                d.sem.release()
            else:
                raise TimeoutError('Wait case to finish timeout')

    def _start_sub_case_thread(
        self,
        dev_res: MultiDevResource,
        case: UnittestMenuCase,
        sub_case_index: int,
        case_start_time: float,
        start_retry: int = DEFAULT_START_RETRY,
    ) -> None:
        """
        Start the thread monitoring on the corresponding dut of the sub-case
        """
        # Allocate the kwargs that pass to '_run'
        _kwargs = {
            'dut': dev_res.dut,
            'dev_res': dev_res,
            'case': case,
            'sub_case_index': sub_case_index,
            'start_retry': start_retry,
            'start_time': case_start_time,
        }

        # Create the thread of the sub-case
        dev_res.thread = Thread(target=self._run, kwargs=_kwargs, daemon=True)
        dev_res.thread.start()
        # Thread starts, acquire the semaphore to block '_wait_multi_dev_case_finish'
        dev_res.sem.acquire()

    def _run(self, **kwargs) -> None:  # type: ignore
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
            unity.UNITY_SUMMARY_LINE_REGEX,  # Means the case finished
        ]
        dut = kwargs['dut']
        dev_res = kwargs['dev_res']
        case = kwargs['case']
        sub_case_index = kwargs['sub_case_index']
        start_retry = kwargs['start_retry']
        start_time = kwargs['start_time']
        # Start the case
        dut.expect_exact(READY_PATTERN_LIST)
        # Retry at defined number of times if not write successfully
        for retry in range(start_retry):
            dut.write(str(case.index))
            try:
                dut.expect_exact(case.name, timeout=1)
                break
            except TIMEOUT as e:
                if retry >= start_retry - 1:
                    dev_res.sem.release()
                    raise e

        dut.write(str(sub_case_index))

        # Wait for the specific patterns, only exist when the sub-case finished
        while True:
            pat = dut.expect(signal_pattern_list, timeout=60)
            if pat is not None:
                match_str = pat.group().decode('utf-8')

                # Send a signal
                if self.SEND_SIGNAL_PREFIX in match_str:
                    send_sig = pat.group(1).decode('utf-8')
                    for d in self.group:
                        d.recv_sig.append(send_sig)

                # Waiting for a signal
                elif self.WAIT_SIGNAL_PREFIX in match_str:
                    wait_sig = pat.group(1).decode('utf-8')
                    while True:
                        if wait_sig in dev_res.recv_sig:
                            dev_res.recv_sig.remove(wait_sig)
                            dut.write('')
                            break
                        # Keep waiting the signal
                        else:
                            time.sleep(0.1)

                # Case finished
                elif 'Tests' in match_str:
                    case_end_time = time.perf_counter()
                    case_duration = case_end_time - start_time
                    additional_attrs = {'time': round(case_duration, 3)}
                    log = utils.remove_asci_color_code(dut.pexpect_proc.before)
                    dut.testsuite.add_unity_test_cases(log, additional_attrs=additional_attrs)
                    break

        # The case finished, release the semaphore to unblock the '_wait_multi_dev_case_finish'
        dev_res.sem.release()

    def run_multi_dev_case(
        self,
        case: UnittestMenuCase,
        reset: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        start_retry: int = DEFAULT_START_RETRY,
    ) -> None:
        """
        Run a specific multi_device case

        Notes:
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
                dev_res.dut.serial.hard_reset()

        start_time = time.perf_counter()
        for sub_case in case.subcases:
            if isinstance(sub_case['index'], str):
                index = int(sub_case['index'], 10)
            else:
                index = sub_case['index']
            self._start_sub_case_thread(
                dev_res=self.group[index - 1],
                case=case,
                sub_case_index=index,
                case_start_time=start_time,
                start_retry=start_retry,
            )
        # Waiting all the devices to finish their test cases
        self._wait_multi_dev_case_finish(timeout=timeout)

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
        if case.type == 'normal':
            self.first_dut._run_normal_case(case, reset=reset, timeout=timeout)
        elif case.type == 'multi_stage':
            self.first_dut._run_multi_stage_case(case, reset=reset, timeout=timeout)
        elif case.type == 'multi_device':
            self.run_multi_dev_case(case, reset=reset, timeout=timeout, start_retry=start_retry)
