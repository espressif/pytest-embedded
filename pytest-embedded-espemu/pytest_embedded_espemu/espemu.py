import logging
import os
import shlex
import socket
import subprocess
import time
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

    SUPPORTED_TARGETS: t.ClassVar[tuple] = ('esp32c3', 'esp32c5', 'esp32c6', 'esp32h2', 'esp32p4', 'esp32s31')

    # esp-emu reads and writes a QEMU compatible eFuse image of this size. A
    # blank one means "nothing burned", which is the state a test starts from
    # unless it is given an image of its own.
    EFUSE_IMAGE_SIZE = 336

    # Boot to the ROM loader instead of the firmware, so esptool and espefuse
    # can drive the emulator over the UART socket. There are no modem control
    # lines on a socket, so the strap has to be set at launch.
    DOWNLOAD_MODE_STRAP = '0x02'

    def __init__(
        self,
        espemu_image_path: str | None = None,
        espemu_prog_path: str | None = None,
        espemu_cli_args: str | None = None,
        espemu_extra_args: str | None = None,
        espemu_efuse_path: str | None = None,
        app: t.Optional['EspEmuApp'] = None,
        **kwargs,
    ):
        """
        Args:
            espemu_image_path: image path (merged flash binary)
            espemu_prog_path: esp-emu program path
            espemu_cli_args: esp-emu CLI arguments
            espemu_extra_args: esp-emu CLI extra arguments, will be appended to `espemu_cli_args`
            espemu_efuse_path: eFuse image the emulator reads at start and writes back on exit
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

        self.espemu_prog_path = espemu_prog_path
        self.image_path = image_path
        self.target = target
        self.efuse_path = espemu_efuse_path

        efuse_args = []
        if self.efuse_path:
            self._create_efuse_image(self.efuse_path)
            logging.debug('The eFuse image will be saved to: %s', self.efuse_path)
            efuse_args = ['--efuse', self.efuse_path]
        # A chip reset has no in-band form — on hardware it is a DTR/RTS toggle
        # into EN, and pyserial's `socket://` handler ignores modem control
        # lines — so it goes over esp-emu's control channel. Older binaries do
        # not have the flag, and passing an unknown one makes them exit, so ask
        # first and stay resettable-or-not accordingly.
        self.control_port: int | None = None
        control_args = []
        if self._supports_control_channel(espemu_prog_path):
            self.control_port = self._free_port()
            control_args = ['--control-tcp', f'127.0.0.1:{self.control_port}']

        cmd = [
            espemu_prog_path,
            '--chip',
            target,
            '--firmware',
            image_path,
            *efuse_args,
            *control_args,
            *shlex.split(espemu_cli_args or ''),
            *shlex.split(espemu_extra_args or ''),
        ]

        super().__init__(cmd=cmd, **kwargs)

    @classmethod
    def _create_efuse_image(cls, path: str) -> None:
        """Create a blank eFuse image, keeping one that already exists."""
        if os.path.exists(path):
            return

        with open(path, 'wb') as f:
            f.write(b'\x00' * cls.EFUSE_IMAGE_SIZE)

    def execute_efuse_command(self, command: str) -> None:
        """
        Run an espefuse command against the emulator.

        A second emulator instance is started in download mode with its UART on
        a socket, since the running one is booted into the firmware and a socket
        carries no reset lines. The instance writes the eFuse image back on
        exit, so the burned bits are there the next time the emulator starts.

        Args:
            command: espefuse command line, e.g. "burn-custom-mac 00:11:22:33:44:55"
        """
        import espefuse

        if not self.efuse_path:
            raise ValueError('No eFuse image set. Please use --espemu-efuse-path')

        available_port = self._free_port()

        child = subprocess.Popen(
            [
                self.espemu_prog_path,
                '--chip',
                self.target,
                '--firmware',
                self.image_path,
                '--efuse',
                self.efuse_path,
                '--strap-mode',
                self.DOWNLOAD_MODE_STRAP,
                '--uart-tcp',
                f'127.0.0.1:{available_port}',
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            self._wait_for_port(available_port)
            args = [arg for arg in shlex.split(command) if arg != '--do-not-confirm']
            espefuse.main(
                [
                    '--port',
                    f'socket://127.0.0.1:{available_port}',
                    '--chip',
                    self.target,
                    '--do-not-confirm',
                    *args,
                ]
            )
        finally:
            child.terminate()
            child.wait(timeout=10)

    @staticmethod
    def _wait_for_port(port: int, timeout: float = 30) -> None:
        """Wait until the emulator accepts connections on its UART socket."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(('127.0.0.1', port)) == 0:
                    return
            time.sleep(0.1)

        raise TimeoutError(f'esp-emu did not open its UART socket on port {port} within {timeout}s')

    @staticmethod
    def _free_port() -> int:
        """An unused local port for one of the emulator's sockets."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return int(s.getsockname()[1])

    @classmethod
    def _supports_control_channel(cls, prog_path: str) -> bool:
        """Whether this esp-emu build accepts `--control-tcp`."""
        try:
            out = subprocess.run([prog_path, '--help'], capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            return False
        return '--control-tcp' in (out.stdout + out.stderr)

    def control_command(self, command: str, timeout: float = 30) -> str:
        """Send one command to the emulator's control channel and return its reply."""
        if self.control_port is None:
            raise NotImplementedError(
                'this esp-emu build has no --control-tcp channel; '
                'a newer emulator is needed for device-state operations'
            )
        with socket.create_connection(('127.0.0.1', self.control_port), timeout=timeout) as sock:
            sock.sendall(f'{command}\n'.encode())
            with sock.makefile('rb') as reader:
                reply = reader.readline().decode().strip()
        if reply.startswith('err:'):
            raise RuntimeError(f'esp-emu rejected {command!r}: {reply}')
        return reply

    def _hard_reset(self):
        """
        Reset the emulated chip, the way a DTR/RTS toggle does on hardware.

        The emulator process keeps running, so the dut's output stream, its
        expect history and the log all continue across the reset.
        """
        self.control_command('reset')
