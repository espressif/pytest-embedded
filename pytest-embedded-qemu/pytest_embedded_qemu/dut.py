from typing import AnyStr

from pytest_embedded.dut import Dut

from .qemu import Qemu


class QemuDut(Dut):
    """
    QEMU dut class
    """

    def __init__(
        self,
        qemu: Qemu,
        **kwargs,
    ) -> None:
        self.qemu = qemu

        super().__init__(**kwargs)

        self._hard_reset_func = self.qemu._hard_reset

    def write(self, s: AnyStr) -> None:
        self.qemu.write(s)

    def hard_reset(self):
        self._hard_reset_func()
