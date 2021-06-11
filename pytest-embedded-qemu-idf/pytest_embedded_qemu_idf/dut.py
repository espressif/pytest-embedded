import multiprocessing
import time
from typing import Optional

from pytest_embedded.dut import Dut
from pytest_embedded.log import DuplicateLogStdout, to_str
from pytest_embedded_idf.app import IdfApp
from pytest_embedded_qemu_idf.qemu import IdfQemu


class IdfQemuDut(Dut):
    """
    IDF QEMU dut class

    :ivar: app: :class:`pytest_embedded_idf.app.IdfApp` instance
    :ivar: qemu: :class:`pytest_embedded_qemu_idf.qemu.IdfQemu` instance
    """

    def __init__(
        self,
        app: Optional[IdfApp] = None,
        qemu: Optional[IdfQemu] = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(app, *args, **kwargs)
        self.qemu = qemu

        with DuplicateLogStdout(self.pexpect_proc, 'creating image'):
            self.qemu.create_image()

        with DuplicateLogStdout(self.pexpect_proc, 'qemu args'):
            self.qemu.start()

        # forward_io_proc would get output from ``self.qemu.qemu_serial_log_file``, do some pre-process jobs and then
        # forward the output to the ``pexpect_proc``, which only accept type str as input
        self.forward_io_proc = self._open_forward_io_process()
        self.forward_io_proc.start()

        self._sessions_close_methods.extend(
            [
                self.forward_io_proc.terminate,
                self.qemu.close,
            ]
        )

    def _open_forward_io_process(self) -> multiprocessing.Process:
        proc = multiprocessing.Process(target=self._forward_io)
        return proc

    @Dut.redirect_stdout('qemu')
    def _forward_io(self):
        time.sleep(1)  # in case the log file is not generate by qemu
        for line in open(self.qemu.log_file):
            print(to_str(line))
