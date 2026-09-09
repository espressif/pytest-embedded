from typing import AnyStr

from pytest_embedded.dut import Dut

from .espemu import EspEmu
from .serial import EspEmuSerial


class EspEmuDut(Dut):
    """
    esp-emu dut class

    Attributes:
        target (str): target chip type, taken from the app
    """

    def __init__(
        self,
        espemu: EspEmu,
        **kwargs,
    ) -> None:
        self.espemu = espemu

        super().__init__(**kwargs)

        # `IdfDut` exposes this for serial runs, and test fixtures use it to
        # select target specific behavior. `EspEmuApp` is an `IdfApp`, so the
        # target is known here as well; keep it optional for other app classes.
        self.target: str | None = getattr(self.app, 'target', None)

        # `IdfSerial` is what ESP-IDF tests call for device state — a reset,
        # an erase, an eFuse burn. Give them something that answers, so a test
        # that needs one reports which operation it needed.
        self.serial = EspEmuSerial(espemu, getattr(self, 'app', None))

        self._hard_reset_func = self.espemu._hard_reset

    def write(self, s: AnyStr) -> None:
        self.espemu.write(s)
