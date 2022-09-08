import datetime
import errno
import logging
import multiprocessing
import os
import subprocess
import sys
import tempfile
import uuid
from multiprocessing import queues
from time import sleep
from typing import AnyStr, List, Union

import pexpect.fdpexpect
from pexpect import EOF, TIMEOUT
from pexpect.utils import poll_ignore_interrupts, select_ignore_interrupts

from .utils import to_bytes, to_str


class MessageQueue(queues.Queue):
    """
    Message Queue

    All the messages would be printed when pushed into the queue
    """

    STDOUT = sys.__stdout__

    # need to be pickled
    ATTRS = [
        '_count',
        '_total',
        '_source',
        '_with_timestamp',
        '_added_prefix',
    ]

    def __init__(self, with_timestamp: bool = True, count: int = 1, total: int = 1, **kwargs):
        super().__init__(**kwargs)

        self._count = count
        self._total = total

        if self._total > 1:
            self._source = f'dut-{self._count}'
        else:
            self._source = None

        # print utils
        self._with_timestamp = with_timestamp
        self._added_prefix = False

    def __getstate__(self):
        state = {k: getattr(self, k) for k in self.ATTRS}
        state['parent_state'] = super().__getstate__()  # noqa
        return state

    def __setstate__(self, state):
        super().__setstate__(state['parent_state'])  # noqa
        del state['parent_state']
        for k in state:
            setattr(self, k, state[k])

    def put(self, obj, **kwargs):
        if not isinstance(obj, (str, bytes)):
            super().put(obj, **kwargs)
            return

        if obj == '' or obj == b'':
            return

        _b = to_bytes(obj)
        _s = to_str(obj)

        prefix = ''
        if self._source:
            prefix = f'[{self._source}] ' + prefix
        if self._with_timestamp:
            prefix = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + prefix

        if not self._added_prefix:
            _s = prefix + _s
            self._added_prefix = True
        _s = _s.replace('\n', '\n' + prefix)
        if prefix and _s.endswith(prefix):
            _s = _s.rsplit(prefix, maxsplit=1)[0]
            self._added_prefix = False

        super().put(_b, **kwargs)
        self.STDOUT.write(_s)
        self.STDOUT.flush()

    def write(self, s: AnyStr):
        self.put(s)

    def flush(self):
        pass

    def isatty(self):
        return True


class PexpectProcess(pexpect.fdpexpect.fdspawn):
    """
    Use a temp file to gather multiple inputs into one output, and do `pexpect.expect()` from one place.
    """

    def read_nonblocking(self, size=1, timeout=-1) -> bytes:
        """
        Since we're using real file stream, here we only raise an EOF errorwhen the file stream has been closed.
        This could solve the `os.read()` blocked issue.

        Args:
            size: most read bytes
            timeout: timeout

        Returns:
            read bytes
        """
        try:
            if os.name == 'posix':
                if timeout == -1:
                    timeout = self.timeout
                rlist = [self.child_fd]
                wlist = []
                xlist = []
                if self.use_poll:
                    rlist = poll_ignore_interrupts(rlist, timeout)
                else:
                    rlist, wlist, xlist = select_ignore_interrupts(rlist, wlist, xlist, timeout)
                if self.child_fd not in rlist:
                    raise TIMEOUT('Timeout exceeded.')

            s = os.read(self.child_fd, size)
        except OSError as err:
            if err.args[0] == errno.EIO:  # Linux-style EOF
                pass
            if err.args[0] == errno.EBADF:  # Bad file descriptor
                raise EOF('Bad File Descriptor')
            raise
        except ValueError as err:
            if err.args[0] == 'file descriptor cannot be a negative integer (-1)':
                raise EOF('Bad File Descriptor')
            raise

        s = self._decoder.decode(s, final=False)
        self._log(s, 'read')
        return s

    def terminate(self, force=False):
        """
        Close the temporary file streams
        """
        self.close()


def live_print_call(*args, **kwargs):
    """
    live print the `subprocess.Popen` process.

    Notes:
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


class DuplicateStdoutMixin:
    """
    A mixin class which provides function `create_forward_io_proc` to create a forward io thread.

    Notes:
        `_forward_io()` should be implemented in subclasses, the function should be something like:

        ```python
        def _forward_io(self, pexpect_proc: PexpectProcess) -> None:
            pexpect_proc.write(...)
        ```
    """

    def __init__(self, msg_queue: multiprocessing.Queue, **kwargs):
        super().__init__(**kwargs)

        self.q = msg_queue
        self._p: multiprocessing.Process = None  # type: ignore

    def _forward_io(self) -> None:
        raise NotImplementedError('should be implemented by subclasses')


class DuplicateStdoutPopen(DuplicateStdoutMixin, subprocess.Popen):
    """
    `subprocess.Popen` with `DuplicateStdoutMixin` mixed with default popen kwargs.
    """

    def __init__(self, cmd: Union[str, List[str]], **kwargs):
        # we use real log file to record output, pipe-like file object won't be non-blocking.
        _log_file = os.path.join(
            tempfile.gettempdir(),
            datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S'),
            f'{uuid.uuid4()}.log',
        )
        parent_dir = os.path.dirname(_log_file)
        if parent_dir:  # in case value is a single file under the current dir
            os.makedirs(os.path.dirname(_log_file), exist_ok=True)
        self._fw = open(_log_file, 'w')
        self._fr = open(_log_file, 'r')
        logging.debug(f'temp log file: {_log_file}')

        kwargs.update(
            {
                'bufsize': 0,
                'stdin': subprocess.PIPE,
                'stdout': self._fw,
                'stderr': self._fw,
            }
        )

        super().__init__(cmd, **kwargs)

    def __del__(self):
        self._fw.close()
        self._fr.close()

    def send(self, s: AnyStr) -> None:
        """
        Write to `stdin` via `stdin.write`.

        If the input is `str`, will encode to `bytes` and add a b'\\n' automatically in the end.

        if the input is `bytes`, will pass this directly.

        Args:
            s: bytes or str
        """
        self.stdin.write(to_bytes(s, '\n'))

    def _forward_io(self, pexpect_proc: PexpectProcess) -> None:
        while self.poll() is None:
            pexpect_proc.write(self._fr.read())
            sleep(0.1)  # set interval
