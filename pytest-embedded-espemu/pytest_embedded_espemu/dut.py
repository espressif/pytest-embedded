from typing import AnyStr

from pytest_embedded.dut import Dut

from .espemu import EspEmu


class EspEmuDut(Dut):
    """
    esp-emu dut class
    """

    def __init__(
        self,
        espemu: EspEmu,
        **kwargs,
    ) -> None:
        self.espemu = espemu

        super().__init__(**kwargs)

        self._hard_reset_func = self.espemu._hard_reset

    def write(self, s: AnyStr) -> None:
        self.espemu.write(s)
