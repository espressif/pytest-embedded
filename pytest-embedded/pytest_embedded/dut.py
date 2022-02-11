import functools
import logging
import os.path
import re
from typing import AnyStr, Callable, Match, Optional, Union

import pexpect

from .app import App
from .log import PexpectProcess
from .unity import UNITY_SUMMARY_LINE_REGEX, TestSuite
from .utils import to_bytes


class Dut:
    """
    Device under test (DUT) base class
    """

    def __init__(
        self, pexpect_proc: PexpectProcess, app: App, pexpect_logfile: str, test_case_name: str, **kwargs
    ) -> None:
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            app: `App` instance
        """
        self.pexpect_proc = pexpect_proc
        self.app = app

        self.logfile = pexpect_logfile
        self.logdir = os.path.dirname(self.logfile)
        logging.info(f'Logs recorded under folder: {self.logdir}')

        self.test_case_name = test_case_name
        self.dut_name = os.path.splitext(os.path.basename(pexpect_logfile))[0]

        for k, v in kwargs.items():
            setattr(self, k, v)

        # junit related
        # TODO: if request.option.xmlpath
        self.testsuite = TestSuite(self.test_case_name)

    def close(self) -> None:
        if self.testsuite.testcases:
            junit_report = os.path.join(self.logdir, f'{self.dut_name}.xml')
            self.testsuite.dump(junit_report)
            logging.info(f'Created unity output junit report: {junit_report}')

    def write(self, *args, **kwargs) -> None:
        """
        Write to `pexpect_proc`. All arguments would pass to `pexpect.spawn.write()`
        """
        self.pexpect_proc.write(*args, **kwargs)

    def _pexpect_func(func) -> Callable[..., Union[Match, AnyStr]]:  # noqa
        @functools.wraps(func)  # noqa
        def wrapper(self, *args, **kwargs) -> Union[Match, AnyStr]:
            try:
                func(self, *args, **kwargs)  # noqa
            except (pexpect.EOF, pexpect.TIMEOUT) as e:
                args = [args] if isinstance(args, str) else args
                debug_str = (
                    f'Not found "{str(args)}" with arguments {str(kwargs)}\n'
                    f'Bytes in current buffer: {self.pexpect_proc.buffer}\n'
                    f'Full pexpect process log file: {self.logfile}'
                )
                raise e.__class__(debug_str) from e
            else:
                if self.pexpect_proc.match in [pexpect.EOF, pexpect.TIMEOUT]:
                    return self.pexpect_proc.before.rstrip()

                return self.pexpect_proc.match

        return wrapper

    @_pexpect_func  # noqa
    def expect(self, *args, **kwargs) -> Match:  # noqa
        """
        Expect from `pexpect_proc`. All the arguments would pass to `pexpect.expect()`.

        Returns:
            AnyStr: if you're matching pexpect.EOF or pexpect.TIMEOUT to get all the current buffers.

        Returns:
            re.Match: if matched given string.
        """
        self.pexpect_proc.expect(*args, **kwargs)

    @_pexpect_func  # noqa
    def expect_exact(self, *args, **kwargs) -> Match:  # noqa
        """
        Expect from `pexpect_proc`. All the arguments would pass to `pexpect.expect_exact()`.

        Returns:
            AnyStr: if you're matching pexpect.EOF or pexpect.TIMEOUT to get all the current buffers.

        Returns:
            re.Match: if matched given string.
        """
        self.pexpect_proc.expect_exact(*args, **kwargs)

    ANSI_ESCAPE_RE = re.compile(
        r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    ''',
        re.VERBOSE,
    )

    @_pexpect_func  # noqa
    def expect_unity_test_output(
        self, remove_asci_escape_code: bool = True, timeout: int = 60, extra_before: Optional[AnyStr] = None
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
            log = to_bytes(extra_before) + self.pexpect_proc.before
        else:
            log = self.pexpect_proc.before

        if remove_asci_escape_code:
            log = self.ANSI_ESCAPE_RE.sub('', log.decode('utf-8', errors='ignore'))

        self.testsuite.add_unity_test_cases(log)
