import errno
import logging
import os
import queue
import subprocess
import tempfile
import textwrap
import threading
import time
import uuid
from typing import AnyStr

import pexpect.fdpexpect
from pexpect import EOF, TIMEOUT
from pexpect.utils import poll_ignore_interrupts, select_ignore_interrupts

from .utils import Meta, remove_asci_color_code, to_bytes, to_str, utcnow_str


class MessageQueue(queue.Queue):
    """
    A thread-safe queue that only accepts non-empty `str`/`bytes` messages.

    Could also be used as a file-like object via `write()`/`flush()`/`isatty()`.
    """

    def put(self, obj, *args, **kwargs):
        if not isinstance(obj, (str, bytes)):
            super().put(obj, *args, **kwargs)
            return

        if obj == '' or obj == b'':
            return

        super().put(to_bytes(obj), *args, **kwargs)

    def write(self, s: AnyStr):
        self.put(s)

    def flush(self):
        pass

    def isatty(self):
        return True


_WATCHDOG_INTERVAL = 5.0  # seconds; module-level so tests can monkeypatch it

_watchdog_lock = threading.Lock()
_watchdog_registry: list['_MonitoredThread'] = []
_watchdog_started = False


class _MonitoredThread(threading.Thread):
    """
    A daemon thread registered with a lightweight watchdog.

    - If an exception escapes ``run()`` (i.e. a bug not handled by the per-message
      ``try/except``), the watchdog reports it loudly - without this, a dead listener
      or redirect thread only surfaces much later as unexplained pexpect timeouts.
    - If ``watch_queue`` is given and the thread stops making progress while the
      queue has a backlog (e.g. blocked on a stalled stdout), the watchdog reports it.
    """

    def __init__(
        self,
        *args,
        watch_name: str | None = None,
        watch_queue: MessageQueue | None = None,
        **kwargs,
    ):
        self._watch_name = watch_name
        self._watch_queue = watch_queue
        self._beat = 0
        self._last_beat = 0
        self._finished = False
        self._died_with_exc = False
        self._alarm_raised = False
        super().__init__(*args, **kwargs)
        with _watchdog_lock:
            _watchdog_registry.append(self)
        _ensure_watchdog()

    def beat(self) -> None:
        """Call once per processed item / loop iteration to prove progress."""
        self._beat += 1

    def run(self) -> None:
        try:
            super().run()
        except BaseException:
            self._died_with_exc = True
            raise
        finally:
            self._finished = True


def _ensure_watchdog() -> None:
    global _watchdog_started
    if _watchdog_started:
        return
    _watchdog_started = True
    threading.Thread(target=_watchdog_main, name='pytest-embedded-watchdog', daemon=True).start()


def _watchdog_main() -> None:
    while True:
        time.sleep(_WATCHDOG_INTERVAL)
        _watchdog_check_once()


def _watchdog_check_once() -> None:
    with _watchdog_lock:
        threads = list(_watchdog_registry)
    for t in threads:
        if t is None:
            # `_close_or_terminate` nulls out list slots that reference the closed object
            # (via gc.get_referrers) - our registry is such a list. Skip the holes.
            continue
        name = t._watch_name or t.name
        if t._finished:
            if t._died_with_exc and not t._alarm_raised:
                t._alarm_raised = True
                logging.error(
                    'watchdog: thread %r died with an exception. '
                    'Output for this DUT will freeze and expects will time out.',
                    name,
                )
            continue
        if t._beat != t._last_beat:
            t._last_beat = t._beat
            t._alarm_raised = False
            continue
        q = t._watch_queue
        if q is not None and q.qsize() > 0 and not t._alarm_raised:
            t._alarm_raised = True
            logging.error(
                'watchdog: thread %r made no progress with %d queued messages '
                '(stdout backpressure?). Output for this DUT will freeze.',
                name,
                q.qsize(),
            )
    # prune holes left by `_close_or_terminate` and fully-reported dead threads,
    # so a long session doesn't accumulate an unbounded registry
    with _watchdog_lock:
        for i in range(len(_watchdog_registry) - 1, -1, -1):
            t = _watchdog_registry[i]
            if t is None or (t._finished and (not t._died_with_exc or t._alarm_raised)):
                del _watchdog_registry[i]


class PexpectProcess(pexpect.fdpexpect.fdspawn):
    """
    Use a temp file to gather multiple inputs into one output, and do `pexpect.expect()` from one place.
    """

    @property
    def buffer_debug_str(self):
        return textwrap.shorten(
            remove_asci_color_code(to_str(self.buffer)),
            width=200,
            placeholder=f'... (total {len(self.buffer)} bytes)',
        )

    def read_nonblocking(self, size: int = 1, timeout: int = -1) -> bytes:
        """
        Since we're using real file stream, here we only raise an EOF error when the file stream has been closed.
        This could solve the `os.read()` blocked issue.

        Args:
            size: Read at most *size* bytes.
            timeout: Wait timeout seconds for file descriptor to be
                ready to read. When -1 (default), use `self.timeout`. When 0, poll.

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

    def terminate(self, force=False):  # noqa
        """
        Close the temporary file stream and itself.
        """
        self.close()


def live_print_call(*args, msg_queue: MessageQueue | None = None, expect_returncode: int = 0, **kwargs):
    """
    live print the `subprocess.Popen` process

    Args:
        msg_queue: `MessageQueue` instance, would redirect to message queue instead of sys.stdout if specified
        expect_returncode: expect return code. (Default 0). Would raise exception when return code is different

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
        if msg_queue:
            msg_queue.put(process.stdout.read())
        else:
            print(to_str(process.stdout.read()))

    if process.returncode != expect_returncode:
        raise subprocess.CalledProcessError(process.returncode, process.args)


class _PopenRedirectThread(_MonitoredThread):
    """
    Keep reading the log file written by the `subprocess.Popen` instance and forward the content
    to the `MessageQueue` instance.
    """

    def __init__(self, msg_queue: MessageQueue, logfile: str):
        self._q = msg_queue
        self.logfile = logfile
        self._stopping = threading.Event()

        super().__init__(
            target=self._forward_io,
            daemon=True,  # killed by the main thread
            watch_name=f'redirect:{os.path.basename(logfile)}',
            watch_queue=msg_queue,
        )

    def _forward_io(self) -> None:
        # Binary mode: the file is still being appended to. A text-mode read finalizes the
        # incremental decoder at every temporary EOF, and a UTF-8 sequence straddling that
        # boundary raises UnicodeDecodeError, silently killing this thread. Decoding is not
        # needed - `MessageQueue.put` re-encodes with `to_bytes`, and the pexpect buffer is bytes.
        while not self._stopping.is_set():
            try:
                fr = open(self.logfile, 'rb')
            except OSError as e:
                logging.error('redirect: cannot open %s (%s). retrying...', self.logfile, e)
                time.sleep(0.5)
                continue

            with fr:
                while not self._stopping.is_set():
                    self.beat()
                    try:
                        _s = fr.read()
                        if _s:
                            self._q.put(_s)
                        else:  # no new content. avoid busy-waiting on the log file
                            time.sleep(0.1)
                    except Exception:
                        # one failed read must not kill the redirect for the whole session
                        logging.error('redirect: failed to forward output, continuing...', exc_info=True)
                        time.sleep(0.1)

    def stop(self) -> None:
        self._stopping.set()
        if self.is_alive():
            self.join(timeout=5)


class DuplicateStdoutPopen(subprocess.Popen):
    """
    Subclass of `subprocess.Popen` that redirect the output into the `MessageQueue` instance
    """

    SOURCE = 'POPEN'
    REDIRECT_CLS = _PopenRedirectThread

    def __init__(self, msg_queue: MessageQueue, cmd: str | list[str] = [], meta: Meta | None = None, **kwargs):
        self._q = msg_queue
        self._p = None

        if meta:
            logdir = meta.logdir
            logfile_extension = meta.logfile_extension
        else:
            logdir = os.path.join(
                tempfile.gettempdir(),
                utcnow_str(),
            )
            os.makedirs(logdir, exist_ok=True)
            logfile_extension = '.log'

        # we use real log file to record output, pipe-like file object won't be non-blocking.
        _log_file = os.path.join(logdir, f'{self.SOURCE.lower()}-{uuid.uuid4()}{logfile_extension}')
        self._fw = open(_log_file, 'w')
        self._logfile = _log_file
        self._logfile_offset = 0
        logging.debug(f'temp log file: {_log_file}')

        self._cmd = cmd

        # Only start subprocess if command is not empty
        if cmd and cmd != []:
            kwargs.update(
                {
                    'bufsize': 0,
                    'stdin': subprocess.PIPE,
                    'stdout': self._fw,
                    'stderr': self._fw,
                }
            )

            logging.info('Executing %s', ' '.join(cmd) if isinstance(cmd, list) else cmd)
            super().__init__(cmd, **kwargs)
        else:
            # For empty commands, initialize minimal subprocess.Popen attributes
            logging.debug('Empty command provided, not starting subprocess')
            self.args = cmd
            self.returncode = None
            self.pid = None
            self.stdin = None
            self.stdout = None
            self.stderr = None

        # some sub classes does not need to redirect to the message queue, they use blocking-IO instead and
        # return the response immediately in `write()`
        if self.REDIRECT_CLS:
            self._p = self.REDIRECT_CLS(msg_queue, _log_file)
            self._p.start()

    def close(self):
        if self._p:
            self._p.stop()

        self._fw.close()

    def terminate(self):
        self.close()

        super().terminate()

    def write(self, s: AnyStr) -> None:
        r"""
        Write to `stdin` via `stdin.write`.

        - If the input is `str`, will encode to `bytes` and add a b'\\n' automatically in the end.
        - If the input is `bytes`, will pass this directly.

        Args:
            s: bytes or str
        """
        logging.debug(f'{self.SOURCE} ->: {to_str(s)}')
        self.stdin.write(to_bytes(s, '\n'))
