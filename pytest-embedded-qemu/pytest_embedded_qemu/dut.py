from typing import AnyStr

from pytest_embedded.app import App
from pytest_embedded.dut import Dut
from pytest_embedded.log import PexpectProcess

from .qemu import Qemu


class QemuDut(Dut):
    """
    QEMU dut class
    """

    def __init__(
        self,
        qemu: Qemu,
        app: App,
        pexpect_proc: PexpectProcess,
        **kwargs,
    ) -> None:
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            app: `App` instance
            qemu: `Qemu` instance
        """
        super().__init__(pexpect_proc, app, **kwargs)
        self.qemu = qemu

        self.qemu.create_forward_io_thread(self.pexpect_proc)

    def write(self, s: AnyStr) -> None:
        """
        Write to qemu process.
        """
        self.qemu.send(s)

    def close(self) -> None:
        self.qemu.terminate()

        super(QemuDut, self).close()
