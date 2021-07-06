import copy
import logging
import multiprocessing
import subprocess
import sys
from functools import wraps
from io import BytesIO, TextIOWrapper
from typing import List, Optional, Union

import pexpect
from pytest_embedded.utils import ProcessContainer, to_bytes, to_str


class PexpectProcess(pexpect.spawn):
    """
    :class:`pexpect.spawn` wrapper with default cmd ``cat``.

    ``cat`` will copy the stdin to stdout which could help to gather multi inputs into one place and do
    :func:`pexpect.expect` over them.
    """

    DEFAULT_CLI_ARGS = ['cat']

    def __init__(self, cmd: Optional[list] = None, **kwargs):
        cmd = cmd or copy.deepcopy(self.DEFAULT_CLI_ARGS)
        super().__init__(cmd, **kwargs, codec_errors='ignore')


class DuplicateStdout(TextIOWrapper):
    """
    Use this in ``with`` statement to log stdout by each line and duplicate them to pexpect process as well.

    use pytest logging functionality to log to cli or file by setting ``log_cli`` related attributes or ``log_file``
    related attributes. These attributes could be set at the same time.

    :param pexpect_proc: pexpect process
    :param source: stdout source, would be a prefix to log, like ``[SOURCE] this line is a log``
    """

    def __init__(self, pexpect_proc: Optional[pexpect.spawn] = None, source: Optional[str] = None):  # noqa
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
        Write string with :func:`logging.info`, and duplicate the string to the pexpect process if it's provided.
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
        We don't need to flush anymore since the write method would directly log in both console and file
        (if provided).
        """
        pass

    def close(self) -> None:
        """
        Revert the redirection of sys.stdout.
        """
        if self.stdout is not None:
            sys.stdout = self.stdout
            self.stdout = None

    def isatty(self) -> bool:
        return True


def live_print_call(*args, **kwargs):
    """
    live print the :func:`subprocess.call` process. Use this function when redirecting ``sys.stdout`` to enable
    live-logging and logging to file simultaneously.

    :note: This function behaves the same as :func:`subprocess.call`, it would block your current process.
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
    A mixin class which provides :meth:`create_forward_io_process` to create a forward io process.

    :note: :meth:`_forward_io` should be implemented in subclasses, the function body should be something like:

        >>> with DuplicateStdout(pexpect_proc, source):
        >>>     # you code here

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._forward_io_proc = None

    def create_forward_io_process(
        self, pexpect_proc: Optional[pexpect.spawn] = None, source: Optional[str] = None
    ) -> None:
        """
        Create a forward_io process if not exists.

        :param pexpect_proc: pexpect process
        :param source: stdout source, would be a prefix to log, like ``[SOURCE] this line is a log``
        """
        if self._forward_io_proc:
            return

        self._forward_io_proc = multiprocessing.Process(target=self._forward_io, args=(pexpect_proc, source))
        self._forward_io_proc.start()

        self.proc_close_methods.append(self._forward_io_proc.terminate)

    def _forward_io(self, pexpect_proc: Optional[pexpect.spawn] = None, source: Optional[str] = None) -> None:
        raise NotImplementedError('should be implemented by subclasses')


class DuplicateStdoutPopen(DuplicateStdoutMixin, subprocess.Popen):
    """
    A :class:`subprocess.Popen` wrapper.

    For the default popen kwargs please refer to :attr:`POPEN_KWARGS`
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
        Terminate the process with SIGTERM, will also terminate the forward io process if created.
        """
        if self._forward_io_proc:
            self._forward_io_proc.terminate()

        super().terminate()

    def send(self, s: Union[bytes, str]) -> None:
        """
        Write the ``bytes`` to :attr:`stdin` via :meth:`stdin.write`.

        If the input is ``str``, will encode to ``bytes`` and add a b'\\n' automatically in the end.

        if the input is ``bytes``, will pass this directly.

        :param s: ``bytes`` or ``str``
        """
        self.stdin.write(to_bytes(s, '\n'))

    def _forward_io(self, pexpect_proc: Optional[BytesIO] = None, source: Optional[str] = None) -> None:
        with DuplicateStdout(pexpect_proc, source):
            for line in self.stdout:
                print(to_str(line))


def cls_redirect_stdout(pexpect_proc: Optional[PexpectProcess] = None, source: Optional[str] = None):
    """
    This is a decorator which will redirect the stdout to the pexpect thread. Should be the outermost decorator
    if there are multi decorators.

    :note: This is used within python classes. For test scripts, use fixture
        :func:`pytest_embedded.plugin.redirect` would be handier.

    :warning: within this decorator, the ``print`` function would be redirected to the
        :func:`pytest_embedded.log.DuplicateStdout.write`. All the ``args`` and ``kwargs`` passed to ``print``
        could be not working as expected.

    :param pexpect_proc: pexpect process
    :param source: stdout source, would be a prefix to log, like ``[SOURCE] this line is a log``
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
