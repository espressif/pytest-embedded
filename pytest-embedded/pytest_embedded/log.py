import copy
import logging
import multiprocessing
import subprocess
import sys
from functools import wraps
from io import TextIOWrapper
from typing import List, Optional, Union

import pexpect
from .utils import ProcessContainer, to_bytes, to_str


class PexpectProcess(pexpect.spawn):
    """
    `pexpect.spawn` instance with default cmd `cat`.

    `cat` will copy the stdin to stdout, that could help to gather multiple inputs into one output, and do
    `pexpect.expect()` from one place.
    """

    DEFAULT_CLI_ARGS = ['cat']

    def __init__(self, cmd: Optional[list] = None, **kwargs):
        cmd = cmd or copy.deepcopy(self.DEFAULT_CLI_ARGS)
        super().__init__(cmd, **kwargs, codec_errors='ignore')
        self.setecho(False)


class DuplicateStdout(TextIOWrapper):
    """
    A context manager to redirect `sys.stdout` to `pexpect_proc` and log by each line.

    use pytest logging functionality to log to cli or file by setting `log_cli` or `log_file` related attributes.
    These attributes could be set at the same time.

    Warning:
        within this context manager, the `print()` would be redirected to `write()`.
        All the `args` and `kwargs` passed to `print()` would be ignored and could be not working as expected.
    """

    def __init__(self, pexpect_proc: Optional[PexpectProcess] = None, source: Optional[str] = None):  # noqa
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            source: where the `sys.stdout` comes from.
                Would set the prefix to the log, like `[SOURCE] this line is a log`
        """
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
            else:
                log_string = data.rstrip().lstrip('\n\r')
            logging.info(log_string)
            sys.stdout = self  # logging info would modify the sys.stdout again, re assigning here

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
    for line in process.stdout:
        print(to_str(line))


class DuplicateStdoutMixin(ProcessContainer):
    """
    A mixin class which provides function `create_forward_io_process` to create a forward io process.

    Note:
        `_forward_io()` should be implemented in subclasses, the function should be something like:

        ```python
        def _forward_io(self, pexpect_proc: Optional[PexpectProcess] = None, source: Optional[str] = None) -> None:
            with DuplicateStdout(pexpect_proc, source):
                # you code here
        ```
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._forward_io_proc = None

    def create_forward_io_process(
        self, pexpect_proc: Optional[PexpectProcess] = None, source: Optional[str] = None
    ) -> None:
        """
        Create a forward io process if not exists.

        Args:
            pexpect_proc: `PexpectProcess` instance
            source: where the `sys.stdout` comes from.
                Would set the prefix to the log, like `[SOURCE] this line is a log`
        """
        if self._forward_io_proc:
            return

        self._forward_io_proc = multiprocessing.Process(target=self._forward_io, args=(pexpect_proc, source))
        self._forward_io_proc.start()

        self.proc_close_methods.append(self._forward_io_proc.terminate)

    def _forward_io(self, pexpect_proc: Optional[PexpectProcess] = None, source: Optional[str] = None) -> None:
        raise NotImplementedError('should be implemented by subclasses')


class DuplicateStdoutPopen(DuplicateStdoutMixin, subprocess.Popen):
    """
    `subprocess.Popen` with `DuplicateStdoutMixin` mixed with default popen kwargs.
    """

    POPEN_KWARGS = {
        'bufsize': 0,
        'stdin': subprocess.PIPE,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'shell': True,
    }

    def __init__(self, cmd: Union[str, List[str]], **kwargs):
        kwargs.update(self.POPEN_KWARGS)
        super().__init__(cmd, **kwargs)

        self.proc_close_methods.append(self.terminate)

    def terminate(self) -> None:
        """
        Terminate the process with `SIGTERM`, will also terminate the forward io process if created.
        """
        if self._forward_io_proc:
            self._forward_io_proc.terminate()

        super().terminate()

    def send(self, s: Union[bytes, str]) -> None:
        """
        Write `s` to `stdin` via `stdin.write`.

        If the input is `str`, will encode to `bytes` and add a b'\\n' automatically in the end.

        if the input is `bytes`, will pass this directly.

        Args:
            s: bytes or str
        """
        self.stdin.write(to_bytes(s, '\n'))

    def _forward_io(self, pexpect_proc: Optional[PexpectProcess] = None, source: Optional[str] = None) -> None:
        with DuplicateStdout(pexpect_proc, source):
            for line in self.stdout:
                print(to_str(line))


def cls_redirect_stdout(pexpect_proc: Optional[PexpectProcess] = None, source: Optional[str] = None):
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
            self_pexpect_proc = getattr(self, 'pexpect_proc', None)
            with DuplicateStdout(pexpect_proc or self_pexpect_proc, source):
                res = func(self, *args, **kwargs)

            return res

        return inner

    return decorator
