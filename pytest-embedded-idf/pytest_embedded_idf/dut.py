from pytest_embedded import PexpectProcess
from pytest_embedded_serial.dut import SerialDut

from .app import IdfApp
from .serial import IdfSerial


class IdfDut(SerialDut):
    XTENSA_TARGETS = ['esp32', 'esp32s2', 'esp32s3']
    RISCV32_TARGETS = ['esp32c3', 'esp32h2', 'esp32c2']

    app: IdfApp
    serial: IdfSerial

    def __init__(self, pexpect_proc: PexpectProcess, app: IdfApp, serial: IdfSerial, **kwargs) -> None:
        """
        Args:
            pexpect_proc: `PexpectProcess` instance
            app: `IdfApp` instance
            serial: `IdfSerial` instance
        """
        super().__init__(pexpect_proc, app, serial, **kwargs)

        self.target = serial.target

    @property
    def toolchain_prefix(self) -> str:
        """
        Returns:
            Toolchain prefix according to the `self.target`
        """
        if self.target in self.XTENSA_TARGETS:
            return f'xtensa-{self.target}-elf-'
        elif self.target in self.RISCV32_TARGETS:
            return f'riscv32-{self.target}-elf-'
        else:
            raise ValueError(f'Unknown target: {self.target}')
