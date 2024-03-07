import typing as t

from pytest_embedded.dut import Dut
from pytest_embedded.log import DuplicateStdoutPopen

from .app import IdfApp


class LinuxDut(Dut):
    """
    Dut class for Linux targets

    Attributes:
        serial (LinuxSerial): `LinuxSerial` instance
    """

    def __init__(
        self,
        serial,
        **kwargs,
    ) -> None:
        self.serial = serial
        super().__init__(**kwargs)

        self._hard_reset_func = self.serial.hard_reset

    def write(self, data: t.AnyStr) -> None:
        self.serial.write(data)


class LinuxSerial(DuplicateStdoutPopen):
    """
    Linux serial Dut class
    """

    def __init__(
        self,
        app: IdfApp,
        **kwargs,
    ) -> None:
        self.app = app

        if not hasattr(self.app, 'target'):
            raise ValueError(f"Idf app not parsable. Please check if it's valid: {self.app.binary_path}")

        if self.app.target != 'linux':
            raise ValueError(f'Targets do not match. App target: {self.app.target}, Cmd target: "linux".')

        super().__init__(cmd=[self.app.elf_file], **kwargs)

    def hard_reset(self) -> None:
        """
        Perform a fake hardware reset
        """
        self.write('\n')
