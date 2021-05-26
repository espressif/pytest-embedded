import logging
import sys
from io import BytesIO, TextIOWrapper
from typing import Optional


class DuplicateLogStdout(TextIOWrapper):
    """
    Use this in ``with`` statement to log stdout by each line and duplicate them to pexpect process as well.

    use pytest logging functionality to log to cli or file by setting ``log_cli`` related attributes or ``log_file``
    related attributes. These attributes could be set at the same time.

    :ivar: pexpect_proc: dut pexpect process
    :ivar: source: stdout source, would be a prefix to log, like [source] log content
    """

    def __init__(self, pexpect_proc: Optional[BytesIO] = None, source: Optional[str] = None):  # noqa
        self.pexpect_proc = pexpect_proc
        self.source = source

        self.stdout = sys.stdout
        sys.stdout = self

    def __enter__(self):
        pass

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
