import shlex
import typing as t

from pytest_embedded.log import DuplicateStdoutPopen

if t.TYPE_CHECKING:
    from .app import EspEmuApp


class EspEmu(DuplicateStdoutPopen):
    """
    esp-emu class (https://github.com/espressif/esp-emulator)

    The emulator runs with UART0 attached to stdio: its output streams
    straight into the pexpect process and `write()` feeds the firmware's
    UART RX via stdin. No sockets are involved.
    """

    SOURCE = 'ESPEMU'

    ESPEMU_PROG_PATH = 'esp-emu'

    SUPPORTED_TARGETS: t.ClassVar[tuple] = ('esp32c3', 'esp32c6', 'esp32h2', 'esp32p4', 'esp32s31')

    def __init__(
        self,
        espemu_image_path: str | None = None,
        espemu_prog_path: str | None = None,
        espemu_cli_args: str | None = None,
        espemu_extra_args: str | None = None,
        app: t.Optional['EspEmuApp'] = None,
        **kwargs,
    ):
        """
        Args:
            espemu_image_path: image path (merged flash binary)
            espemu_prog_path: esp-emu program path
            espemu_cli_args: esp-emu CLI arguments
            espemu_extra_args: esp-emu CLI extra arguments, will be appended to `espemu_cli_args`
            app: `EspEmuApp` instance, used to detect the target chip
        """
        self.app = app

        image_path = espemu_image_path
        if not image_path and self.app:
            image_path = self.app.image_path
        if not image_path:
            raise ValueError('Please specify --espemu-image-path or use the espemu service together with idf')

        target = getattr(self.app, 'target', None)
        if target not in self.SUPPORTED_TARGETS:
            raise ValueError(
                f'esp-emu does not support target {target!r}. Supported targets: {", ".join(self.SUPPORTED_TARGETS)}'
            )

        espemu_prog_path = espemu_prog_path or self.ESPEMU_PROG_PATH

        cmd = [
            espemu_prog_path,
            '--chip',
            target,
            '--firmware',
            image_path,
            *shlex.split(espemu_cli_args or ''),
            *shlex.split(espemu_extra_args or ''),
        ]

        super().__init__(cmd=cmd, **kwargs)

    def _hard_reset(self):
        """
        esp-emu has no reset API. Raising `NotImplementedError` makes
        `IdfUnityDutMixin` fall back to re-triggering the Unity test menu
        with a newline instead of resetting the target.
        """
        raise NotImplementedError('esp-emu does not support resetting; relaunch the emulator instead')
