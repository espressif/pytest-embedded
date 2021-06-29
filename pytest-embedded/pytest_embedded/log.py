import logging
import multiprocessing
import subprocess
import sys
from io import BytesIO, TextIOWrapper
from typing import List, Optional, Union


class DuplicateLogStdout(TextIOWrapper):
    """
    Use this in ``with`` statement to log stdout by each line and duplicate them to pexpect process as well.

    use pytest logging functionality to log to cli or file by setting ``log_cli`` related attributes or ``log_file``
    related attributes. These attributes could be set at the same time.

    :param pexpect_proc: dut pexpect process
    :param source: stdout source, would be a prefix to log, like ``[SOURCE] this line is a log``
    """

    def __init__(self, pexpect_proc: Optional[BytesIO] = None, source: Optional[str] = None):  # noqa
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
        Write string with :func:`logging.info`, and duplicate the string to the pexpect process if it's provided
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
        We don't need to flush anymore since the write method would directly log in both console and file (if provided)
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


def to_str(bytes_str: Union[bytes, str]) -> str:
    """
    :param bytes_str: ``bytes`` or ``str``
    :return: utf8-decoded string
    """
    if isinstance(bytes_str, bytes):
        return bytes_str.decode('utf-8', errors='ignore')
    return bytes_str


def to_bytes(bytes_str: Union[bytes, str], ending: Optional[Union[bytes, str]] = None) -> bytes:
    """
    :param bytes_str: ``bytes`` or ``str``
    :param ending: ``bytes`` or ``str``, will add to the end of the result
    :return: utf8-encoded bytestring. A ``b'\\n'`` will be added at the end of the bytestring.
    """
    if isinstance(bytes_str, str):
        bytes_str = bytes_str.encode()

    if ending:
        if isinstance(ending, str):
            ending = ending.encode()
        return bytes_str + ending

    return bytes_str


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


class LivePrintPopen(subprocess.Popen):
    """
    Popen with :class:`pytest_embedded.log.DuplicateLogStdout`, could create another process to print the stdout.

    For the default popen kwargs please refer to :attr:`POPEN_KWARGS`
    """

    POPEN_KWARGS = {
        'bufsize': 0,
        'stdin': subprocess.PIPE,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'shell': True,
    }

    def __init__(self, cmd: Union[str, List[str]], *args, **kwargs):

        self._forward_io_proc = None

        self._sessions_close_methods = [
            self.terminate,
        ]

        kwargs.update(self.POPEN_KWARGS)

        super().__init__(cmd, *args, **kwargs)

    def terminate(self) -> None:
        if self._forward_io_proc:
            self._forward_io_proc.terminate()

        super().terminate()

    def send(self, s: Union[bytes, str]) -> None:
        """
        Write the ``bytes`` or ``str`` via :func:`self.proc.stdin.write`. Will encode the string if it's a ``str``.
        Will add a b'\\n' automatically in the end of the ``bytes``.

        :param s: ``bytes`` or ``str``
        """
        self.stdin.write(to_bytes(s, '\n'))

    def create_forward_io_process(self, pexpect_proc: Optional[BytesIO] = None, source: Optional[str] = None) -> None:
        """
        Create a forward_io process

        :param pexpect_proc: pexpect process
        :param source: optional prefix of the log
        """
        if self._forward_io_proc:
            return

        self._forward_io_proc = multiprocessing.Process(target=self._forward_io, args=(pexpect_proc, source))
        self._forward_io_proc.start()

        self._sessions_close_methods.append(self._forward_io_proc.terminate)

    def _forward_io(self, pexpect_proc: Optional[BytesIO] = None, source: Optional[str] = None) -> None:
        with DuplicateLogStdout(pexpect_proc, source):
            for line in self.stdout:
                print(to_str(line))
