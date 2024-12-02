from pytest_embedded_qemu import Qemu, QemuDut

from .dut import NuttxDut


class NuttxQemuDut(QemuDut, NuttxDut):
    """
    DUT class for QEMU usage of the NuttX RTOS.
    """

    def __init__(
        self,
        qemu: Qemu,
        **kwargs,
    ) -> None:
        self.qemu = qemu

        super().__init__(qemu=qemu, **kwargs)

    def reset(self) -> None:
        """Hard reset the DUT."""
        self.hard_reset()
