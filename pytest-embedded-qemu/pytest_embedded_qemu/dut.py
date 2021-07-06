from typing import Optional

import pexpect
from pytest_embedded.app import App
from pytest_embedded.dut import Dut

from .qemu import Qemu


class QemuDut(Dut):
    """
    QEMU dut class

    :ivar: app: :class:`pytest_embedded.app.App` or subclass instance
    :ivar: qemu: :class:`pytest_embedded_qemu_idf.qemu.IdfQemu` instance
    """

    def __init__(
        self,
        qemu: Qemu,
        app: Optional[App] = None,
        pexpect_proc: Optional[pexpect.spawn] = None,
        **kwargs,
    ) -> None:
        super().__init__(app, pexpect_proc, **kwargs)
        self.qemu = qemu

        self.qemu.create_forward_io_process(self.pexpect_proc, source='qemu')

        self.proc_close_methods.append(self.qemu.terminate)
