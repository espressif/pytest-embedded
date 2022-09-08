import functools
import logging
import multiprocessing
import os.path
import textwrap
from typing import AnyStr, Callable, List, Match, Optional, Union

import pexpect

from .app import App
from .log import PexpectProcess
from .unity import UNITY_SUMMARY_LINE_REGEX, TestSuite
from .utils import remove_asci_color_code, to_bytes, to_list, to_str


class Dut:
    """
    Device under test (DUT) base class

    Attributes:
        app (App): `App` instance
        logfile (str): log file path
        logdir (str): log folder path
        test_case_name (str): test case name
    """

    def __init__(
        self,
        pexpect_proc: PexpectProcess,
        msg_queue: multiprocessing.Queue,
        app: App,
        pexpect_logfile: str,
        test_case_name: str,
        **kwargs,
    ) -> None:
        self._p = pexpect_proc
        self._q = msg_queue

        self.app = app
        self.logfile = pexpect_logfile
        self.logdir = os.path.dirname(self.logfile)
        logging.info(f'Logs recorded under folder: {self.logdir}')

        self.test_case_name = test_case_name

        for k, v in kwargs.items():
            setattr(self, k, v)

        # junit related
        self.testsuite = TestSuite(self.test_case_name)

    def close(self) -> None:
        if self.testsuite.testcases:
            junit_report = os.path.splitext(self.logfile)[0] + '.xml'
            self.testsuite.dump(junit_report)
            logging.info(f'Created unity output junit report: {junit_report}')

    def write(self, s: AnyStr) -> None:
        """
        Write to message queue
        """
        self._q.put(to_bytes(s))

    def _pexpect_func(func) -> Callable[..., Union[Match, AnyStr]]:  # noqa
        @functools.wraps(func)  # noqa
        def wrapper(
            self, pattern, *args, expect_all: bool = False, **kwargs
        ) -> Union[Union[Match, AnyStr], List[Union[Match, AnyStr]]]:
            patterns = to_list(pattern)
            res = []
            while patterns:
                try:
                    index = func(self, pattern, *args, **kwargs)  # noqa
                except (pexpect.EOF, pexpect.TIMEOUT) as e:
                    wrapped_buffer_bytes = textwrap.shorten(
                        remove_asci_color_code(to_str(self._p.buffer)),
                        width=200,
                        placeholder=f'... (total {len(self._p.buffer)} bytes)',
                    )
                    debug_str = (
                        f'Not found "{str(pattern)}"\n'
                        f'Bytes in current buffer (color code eliminated): {wrapped_buffer_bytes}\n'
                        f'Please check the full log here: {self.logfile}'
                    )
                    raise e.__class__(debug_str) from e
                else:
                    if self._p.match in [pexpect.EOF, pexpect.TIMEOUT]:
                        res.append(self._p._before.rstrip())
                    else:
                        res.append(self._p.match)

                if expect_all:
                    patterns.pop(index)
                else:
                    break  # one succeeded. leave the loop

            if len(res) == 1:
                return res[0]

            return res

        return wrapper

    @_pexpect_func  # noqa
    def expect(self, pattern, **kwargs) -> Match:  # noqa
        """
        Expect from `pexpect_proc`. All the arguments would pass to `pexpect.expect()`.

        Returns:
            AnyStr: if you're matching pexpect.EOF or pexpect.TIMEOUT to get all the current buffers.

        Returns:
            re.Match: if matched given string.
        """
        return self._p.expect(pattern, **kwargs)

    @_pexpect_func  # noqa
    def expect_exact(self, pattern, **kwargs) -> Match:  # noqa
        """
        Expect from `pexpect_proc`. All the arguments would pass to `pexpect.expect_exact()`.

        Returns:
            AnyStr: if you're matching pexpect.EOF or pexpect.TIMEOUT to get all the current buffers.

        Returns:
            re.Match: if matched given string.
        """
        return self._p.expect_exact(pattern, **kwargs)

    def expect_unity_test_output(
        self,
        remove_asci_escape_code: bool = True,
        timeout: int = 60,
        extra_before: Optional[AnyStr] = None,
    ) -> None:
        """
        Expect a unity test summary block and parse the output into junit report.

        Would combine the junit report into the main one if you use `pytest --junitxml` feature.

        Args:
            remove_asci_escape_code: remove asci escape code in the message field. (default: True)
            timeout: timeout. (default: 60 seconds)
            extra_before: would append before the expected bytes.
                Use this argument when need to run `expect` functions between one unity test call.

        Notes:
            Would raise AssertionError at the end of the test if any unity test case result is "FAIL"
        """
        self.expect(UNITY_SUMMARY_LINE_REGEX, timeout=timeout)

        if extra_before:
            log = to_bytes(extra_before) + self._p.before
        else:
            log = self._p.before

        if remove_asci_escape_code:
            log = remove_asci_color_code(log)

        self.testsuite.add_unity_test_cases(log)
