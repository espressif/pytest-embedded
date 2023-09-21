import functools
import logging
import multiprocessing
import os.path
import time
from typing import AnyStr, Callable, List, Match, Optional, Union

import pexpect

from .app import App
from .log import PexpectProcess
from .unity import UNITY_SUMMARY_LINE_REGEX, TestSuite
from .utils import Meta, _InjectMixinCls, remove_asci_color_code, to_bytes, to_list


class Dut(_InjectMixinCls):
    """
    Device under test (DUT) base class

    Attributes:
        pexpect_proc (PexpectProcess): `PexpectProcess` instance
        app (App): `App` instance
        logfile (str): log file path
        test_case_name (str): test case name
    """

    def __init__(
        self,
        pexpect_proc: PexpectProcess,
        msg_queue: multiprocessing.Queue,
        app: App,
        pexpect_logfile: str,
        test_case_name: str,
        meta: Optional[Meta] = None,
        **kwargs,
    ) -> None:
        self._q = msg_queue
        self._meta = meta

        self.pexpect_proc = pexpect_proc
        self.pexpect_sources = {'default': [pexpect_proc, pexpect_logfile]}
        self.app = app
        self.logfile = pexpect_logfile
        self.test_case_name = test_case_name

        for k, v in kwargs.items():
            setattr(self, k, v)

        # junit related
        self.testsuite = TestSuite(self.test_case_name)

    @property
    def logdir(self):
        return self._meta.logdir

    def close(self) -> None:
        if self.testsuite.testcases:
            junit_report = os.path.splitext(self.logfile)[0] + '.xml'
            self.testsuite.dump(junit_report)
            logging.info(f'Created unity output junit report: {junit_report}')

    def write(self, s: AnyStr) -> None:
        """
        Write to the `MessageQueue` instance
        """
        self._q.put(to_bytes(s))

    def _pexpect_func(func) -> Callable[..., Union[Match, AnyStr]]:  # noqa
        @functools.wraps(func)  # noqa
        def wrapper(
            self, pattern, *args, expect_all: bool = False, **kwargs
        ) -> Union[Union[Match, AnyStr], List[Union[Match, AnyStr]]]:
            patterns = to_list(pattern)
            res = []
            _pexpect_proc = kwargs.pop('pexpect_process')
            _logfile = kwargs.pop('pexpect_logfile')
            while patterns:
                try:
                    index = func(self, pattern, _pexpect_proc, *args, **kwargs)  # noqa
                except (pexpect.EOF, pexpect.TIMEOUT) as e:
                    debug_str = (
                        f'Not found "{str(pattern)}"\n'
                        f'Bytes in current buffer (color code eliminated): {_pexpect_proc.buffer_debug_str}\n'
                        f'Please check the full log here: {_logfile}'
                    )
                    raise e.__class__(debug_str) from e
                else:
                    if _pexpect_proc.match in [pexpect.EOF, pexpect.TIMEOUT]:
                        res.append(_pexpect_proc.before.rstrip())
                    else:
                        res.append(_pexpect_proc.match)

                if expect_all:
                    patterns.pop(index)
                else:
                    break  # one succeeded. leave the loop

            if len(res) == 1:
                return res[0]

            return res

        return wrapper

    def register_additional_expect_sources(self, sources=None):
        if sources is not None:
            self.pexpect_sources.update(sources)

        from .log import DuplicateStdoutPopen

        for k in self.__dict__:
            if isinstance(getattr(self, k), DuplicateStdoutPopen):
                self.pexpect_sources[k] = [getattr(self, k).pexpect_proc, getattr(self, k)._logfile]  # noqa

    @_pexpect_func  # noqa
    def _expect(self, pattern, _pexpect_proc, **kwargs) -> Match:  # noqa
        """
        Expect the `pattern` from the internal buffer. All the arguments will be passed to `pexpect.expect()`.

        Args:
            pattern: string, or compiled regex, or a list of string and compiled regex.

        Keyword Args:
            timeout (float): would raise `pexpect.TIMEOUT` exception when pattern is not matched after timeout
            expect_all (bool): need to match all specified patterns if this flag is `True`.
                Otherwise match any of them could pass

        Returns:
            `AnyStr` or `re.Match`

            - `AnyStr`: if you're matching `pexpect.EOF` or `pexpect.TIMEOUT` to get all the current buffers.
            - `re.Match`: if matched given string.
        """
        return _pexpect_proc.expect(pattern, **kwargs)

    def expect(self, pattern, *, source='default', **kwargs):
        if source != 'all':
            pr, lg = self.pexpect_sources[source]
            kwargs['pexpect_process'] = pr
            kwargs['pexpect_logfile'] = lg
            return self._expect(pattern, **kwargs)

        _res = []
        _timeout = kwargs.get('timeout', 30)
        start = time.perf_counter()
        for pr, lg in self.pexpect_sources.values():
            kwargs['timeout'] = _timeout - (time.perf_counter() - start)
            kwargs['pexpect_process'] = pr
            kwargs['pexpect_logfile'] = lg
            _res.append(self._expect(pattern, **kwargs))

        return _res

    @_pexpect_func  # noqa
    def expect_exact(self, pattern, **kwargs) -> Match:  # noqa
        """
        Expect the `pattern` from the internal buffer. All the arguments will be passed to `pexpect.expect_exact()`.

        Args:
            pattern: string, or a list of string

        Keyword Args:
            timeout (float): would raise `pexpect.TIMEOUT` exception when pattern is not matched after timeout
            expect_all (bool): need to match all specified patterns if this flag is `True`.
                Otherwise match any of them could pass

        Returns:
            `AnyStr` or `re.Match`

            - `AnyStr`: if you're matching `pexpect.EOF` or `pexpect.TIMEOUT` to get all the current buffers.
            - `re.Match`: if matched given string.
        """
        return self.pexpect_proc.expect_exact(pattern, **kwargs)

    def expect_unity_test_output(
        self,
        remove_asci_escape_code: bool = True,
        timeout: float = 60,
        extra_before: Optional[AnyStr] = None,
    ) -> None:
        """
        Expect a unity test summary block and parse the output into junit report.

        Would combine the junit report into the main one if you use ``pytest --junitxml`` feature.

        Args:
            remove_asci_escape_code: remove asci escape code in the message field. (default: True)
            timeout: timeout. (default: 60 seconds)
            extra_before: would append before the expected bytes.
                Use this argument when need to run `expect` functions between one unity test call.

        Note:
            - Would raise AssertionError at the end of the test if any unity test case result is "FAIL"
            - Would raise TIMEOUT exception at the end of the test \
                if any unity test case execution took longer than timeout value

        Warning:
            - All unity test cases record would be missed if the final report block is uncaught.
        """
        self.expect(UNITY_SUMMARY_LINE_REGEX, timeout=timeout)

        if extra_before:
            log = to_bytes(extra_before) + self.pexpect_proc.before
        else:
            log = self.pexpect_proc.before

        if remove_asci_escape_code:
            log = remove_asci_color_code(log)

        self.testsuite.add_unity_test_cases(log)

    @_InjectMixinCls.require_services('idf')
    def run_all_single_board_cases(
        self,
        group: Optional[str] = None,
        reset: bool = False,
        timeout: float = 30,
        run_ignore_cases: bool = False,
    ) -> None:
        """
        Run all multi_stage cases

        Args:
            group: test case group
            reset: whether to perform a hardware reset before running a case
            timeout: timeout. (Default: 30 seconds)
            run_ignore_cases: run ignored test cases or not

        Warning:
            requires enable service ``idf``
        """
        pass
