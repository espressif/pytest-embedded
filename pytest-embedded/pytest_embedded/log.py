import logging
import subprocess
import sys
from io import BytesIO, TextIOWrapper
from typing import Optional, Union


class DuplicateLogStdout(TextIOWrapper):
    """
    Use this in ``with`` statement to log stdout by each line and duplicate them to pexpect process as well.

    use pytest logging functionality to log to cli or file by setting ``log_cli`` related attributes or ``log_file``
    related attributes. These attributes could be set at the same time.

    :param: pexpect_proc: dut pexpect process
    :param: source: stdout source, would be a prefix to log, like ``[SOURCE] this line is a log``
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
                log_string = f'[{self.source}] {data.strip()}'
            else:
                log_string = data.strip()
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


def to_str(byte_str: Union[bytes, str]) -> str:
    """
    :param byte_str: bytes or str
    :return: use utf8 to decode the input if it's ``bytes``, otherwise return the input directly
    """
    if isinstance(byte_str, bytes):
        return byte_str.decode('utf-8', errors='ignore')
    return byte_str


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
