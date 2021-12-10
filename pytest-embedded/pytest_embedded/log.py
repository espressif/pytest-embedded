import logging
import os
import subprocess
import sys
from functools import wraps
from io import TextIOWrapper
from typing import Optional

from .utils import FileDescSpawn, to_str


class PexpectProcess(FileDescSpawn):
    """
    TODO
    """

    DUT_PREFIX = 'dut'

    def __init__(self, count: int = 1, total: int = 1, **kwargs):
        self._count = count
        self._total = total

        if self._total > 1:
            self.source = f'{self.DUT_PREFIX}-{self._count}'
        else:
            self.source = None

        # read pipe is used as gathered output, write pipe is used as read pipe
        self.r_pipe, self.w_pipe = os.pipe()

        super().__init__(self.r_pipe, **kwargs)
        # self.logfile_send = self._logfile_fw  # only log output, since the input is the same

    def send(self, s):
        s = self._coerce_send_string(s)

        b = self._encoder.encode(s, final=False)
        return os.write(self.w_pipe, b)


class DuplicateStdout(TextIOWrapper):
    """
    A context manager to duplicate the `sys.stdout` to the specified file descriptor and use `logging` module to log
     the `sys.stdout` at the same time.

    use pytest logging functionality to log to cli or file by setting `log_cli` or `log_file` related attributes.
    These attributes could be set at the same time.

    Warning:
        within this context manager, the `print()` would be redirected to `write()`.
        All the `args` and `kwargs` passed to `print()` would be ignored and could be not working as expected.
    """

    def __init__(self, pexpect_proc: PexpectProcess, source: Optional[str] = None):  # noqa
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            source: where the `sys.stdout` comes from.
                Would set the prefix to the log, like `[SOURCE] this line is a log`
        """
        # DO NOT call super().__init__(), use TextIOWrapper as parent class only for types and functions
        self.pexpect_proc = pexpect_proc
        self.source = source

        self.stdout = None

    def __enter__(self):
        if self.stdout is None:
            self.stdout = sys.stdout
            sys.stdout = self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def write(self, data) -> None:
        """
        Write string with `logging.info()`, and duplicate the string to `pexpect_proc` if specified.
        """
        if data.strip():
            if self.source:
                log_string = '[{}] {}'.format(self.source, data.rstrip().lstrip('\n\r'))
                if self.pexpect_proc and self.pexpect_proc.source:
                    log_string = f'[{self.pexpect_proc.source}]' + log_string
            else:
                log_string = data.rstrip().lstrip('\n\r')
            logging.info(log_string)
            sys.stdout = self  # logging info would modify the sys.stdout again, re-assigning here

        if self.pexpect_proc:
            self.pexpect_proc.write(data)

    def flush(self) -> None:
        """
        Don't need to flush anymore since the write method would directly log the `sys.stdout`.
        """
        pass

    def close(self) -> None:
        """
        Stop redirecting `sys.stdout`.
        """
        if self.stdout is not None:
            sys.stdout = self.stdout
            self.stdout = None

    def isatty(self) -> bool:
        """
        Returns:
            True since it has `write()`.
        """
        return True


def live_print_call(*args, **kwargs):
    """
    live print the `subprocess.Popen` process. Use this function when redirecting `sys.stdout` to enable
    live-logging and logging to file simultaneously.

    Note:
        This function behaves the same as `subprocess.call()`, it would block your current process.
    """
    default_kwargs = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
    }
    default_kwargs.update(kwargs)

    process = subprocess.Popen(*args, **default_kwargs)
    while process.poll() is None:
        print(to_str(process.stdout.read()))


def cls_duplicate_stdout(pexpect_proc: Optional[PexpectProcess] = None, source: Optional[str] = None):
    """
    A decorator which redirects the stdout to the pexpect thread. Should be the outermost decorator
    if there are multiple decorators.

    Note:
        This is used within python classes. For test scripts, fixture `redirect` would be handier.

    Args:
        pexpect_proc: `PexpectProcess` instance
        source: where the `sys.stdout` comes from.
            Would set the prefix to the log, like `[SOURCE] this line is a log`
    """

    def decorator(func):
        @wraps(func)
        def inner(self, *args, **kwargs):
            with DuplicateStdout(pexpect_proc or self.pexpect_proc, source):
                res = func(self, *args, **kwargs)

            return res

        return inner

    return decorator
