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
        super().__init__(**kwargs)

        self.qemu = qemu

    def write(self, s: AnyStr) -> None:
        self.qemu.write(s)
