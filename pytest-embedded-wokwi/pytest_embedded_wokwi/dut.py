from typing import AnyStr

from pytest_embedded.dut import Dut

from .wokwi import Wokwi


class WokwiDut(Dut):
    """
    Wokwi DUT class
    """

    def __init__(
        self,
        wokwi: Wokwi,
        **kwargs,
    ) -> None:
        self.wokwi = wokwi

        super().__init__(**kwargs)

        self._hard_reset_func = self.wokwi._hard_reset

    def write(self, s: AnyStr) -> None:
        self.wokwi.write(s)
