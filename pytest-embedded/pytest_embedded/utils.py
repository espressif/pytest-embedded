import errno
import logging
import os
from threading import Thread
from typing import Optional, Union

from pexpect import EOF, TIMEOUT
from pexpect.fdpexpect import fdspawn


class ProcessContainer:
    """
    Auto call functions under `proc_close_methods` when being garbage collected or `close()`

    Attributes:
        proc_close_methods (list[callable]): A list to collect all the methods that need to be run.
    """

    def __init__(self, *args, **kwargs):
        self.proc_close_methods = []
        super().__init__(*args, **kwargs)

    def __del__(self):
        self.close()

    def close(self) -> None:
        """
        Call all the sessions/threads/processes terminate methods defined in `proc_close_methods`
        """
        for func in getattr(self, 'proc_close_methods', []):
            try:
                func()
            except Exception as e:
                logging.error(e)


def to_str(bytes_str: Union[bytes, str]) -> str:
    """
    Turn `bytes` or `str` to `str`

    Args:
        bytes_str: `bytes` or `str`

    Returns:
        utf8-decoded string
    """
    if isinstance(bytes_str, bytes):
        return bytes_str.decode('utf-8', errors='ignore')
    return bytes_str


def to_bytes(bytes_str: Union[bytes, str], ending: Optional[Union[bytes, str]] = None) -> bytes:
    """
    Turn `bytes` or `str` to `bytes`

    Args:
        bytes_str: `bytes` or `str`
        ending: `bytes` or `str`, will add to the end of the result.
            Only works when the `bytes_str` is `str`

    Returns:
        utf8-encoded bytes
    """
    if isinstance(bytes_str, str):
        bytes_str = bytes_str.encode()

        if ending:
            if isinstance(ending, str):
                ending = ending.encode()
            return bytes_str + ending

    return bytes_str


class ReadThread(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None, timeout=None) -> None:
        super().__init__(group=group, target=target, name=name, args=args, kwargs=kwargs, daemon=daemon)
        self.timeout = timeout
        self.data = b''  # default as empty bytes

    def run(self) -> None:
        if self._target is not None:  # noqa
            self.data = self._target(*self._args, **self._kwargs)  # noqa

    def join(self, timeout: Optional[int] = None) -> bytes:
        timeout = timeout if timeout is not None else self.timeout
        super().join(timeout)
        return self.data


class FileDescSpawn(fdspawn):
    def read_nonblocking(self, size=1, timeout=-1):
        if os.name == 'posix':
            # for POSIX go to the pexpect fdspawn one
            return super().read_nonblocking(size, timeout)

        if not timeout:
            # set a default timeout value to windows. otherwise would be permanently blocked at os.read().
            timeout = 30

        try:
            read_thread = ReadThread(target=os.read, args=(self.child_fd, size), timeout=timeout)
            read_thread.daemon = True  # Mark this thread as daemon thread in case won't block main process exit
            read_thread.start()
            s = read_thread.join(timeout)
            if read_thread.is_alive():
                raise TIMEOUT('Timeout exceeded.')
        except OSError as err:
            if err.args[0] == errno.EIO:
                # Linux-style EOF
                self.flag_eof = True
                raise EOF('End Of File (EOF). Exception style platform.')
            raise

        if s == b'':
            self.flag_eof = True
            raise EOF('End Of File (EOF). Empty string style platform.')

        s = self._decoder.decode(s, final=False)
        self._log(s, 'read')
        return s
