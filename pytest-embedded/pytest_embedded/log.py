import datetime
import errno
import logging
import multiprocessing
import os
import subprocess
import tempfile
import uuid
from multiprocessing import queues
from typing import AnyStr, List, Optional, Union

import pexpect.fdpexpect
from pexpect import EOF, TIMEOUT
from pexpect.utils import poll_ignore_interrupts, select_ignore_interrupts

from .utils import Meta, to_bytes, to_str


class MessageQueue(queues.Queue):
    def put(self, obj, **kwargs):
        if not isinstance(obj, (str, bytes)):
            super().put(obj, **kwargs)
            return

        if obj == '' or obj == b'':
            return

        _b = to_bytes(obj)
        try:
            super().put(_b, **kwargs)
        except:  # noqa # queue might be closed
            pass

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
        Since we're using real file stream, here we only raise an EOF error when the file stream has been closed.
        This could solve the `os.read()` blocked issue.

        :return: String containing the bytes read

        Args:
            size (int): Read at most *size* bytes.
            timeout (int): Wait timeout seconds for file descriptor to be
                ready to read. When -1 (default), use self.timeout. When 0, poll.

        Returns:
            String containing the bytes read
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
        Close the temporary file stream and itself.
        """
        self.close()


def live_print_call(*args, msg_queue: Optional[MessageQueue] = None, expect_returncode: int = 0, **kwargs):
    """
    live print the `subprocess.Popen` process

    Args:
        msg_queue: `MessageQueue` instance, would redirect to message queue instead of sys.stdout if specified
        expect_returncode: expect return code. (Default 0). Would raise exception when return code is different

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
        if msg_queue:
            msg_queue.put(process.stdout.read())
        else:
            print(to_str(process.stdout.read()))

    if process.returncode != expect_returncode:
        raise subprocess.CalledProcessError(process.returncode, process.args)


class _PopenRedirectProcess(multiprocessing.Process):
    def __init__(self, msg_queue: MessageQueue, logfile: str):
        self._q = msg_queue

        self.logfile = logfile

        super().__init__(target=self._forward_io, daemon=True)  # killed by the main process

    def _forward_io(self) -> None:
        with open(self.logfile) as fr:
            while True:
                self._q.put(fr.read())


class DuplicateStdoutPopen(subprocess.Popen):
    """
    Subclass of `subprocess.Popen` that redirect the output into the `MessageQueue` instance
    """

    SOURCE = 'POPEN'
    REDIRECT_CLS = _PopenRedirectProcess

    def __init__(self, msg_queue: MessageQueue, cmd: Union[str, List[str]], meta: Optional[Meta] = None, **kwargs):
        self._q = msg_queue
        self._p = None

        if meta:
            logdir = meta.logdir
        else:
            logdir = os.path.join(
                tempfile.gettempdir(),
                datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S'),
            )
            os.makedirs(logdir, exist_ok=True)

        # we use real log file to record output, pipe-like file object won't be non-blocking.
        _log_file = os.path.join(logdir, f'{self.SOURCE}-{uuid.uuid4()}.log')
        self._fw = open(_log_file, 'w')
        self._logfile = _log_file
        self._logfile_offset = 0
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

        # some sub classes does not need to redirect to the message queue, they use blocking-IO instead and
        # return the response immediately in `write()`
        if self.REDIRECT_CLS:
            self._p = self.REDIRECT_CLS(msg_queue, _log_file)
            self._p.start()

    def close(self):
        if self._p:
            self._p.terminate()

        self._fw.close()

    def terminate(self):
        self.close()

        super().terminate()

    def write(self, s: AnyStr) -> None:
        """
        Write to `stdin` via `stdin.write`.

        If the input is `str`, will encode to `bytes` and add a b'\\n' automatically in the end.

        if the input is `bytes`, will pass this directly.

        Args:
            s: bytes or str
        """
        logging.debug(f'{self.SOURCE} ->: {to_str(s)}')
        self.stdin.write(to_bytes(s, '\n'))
