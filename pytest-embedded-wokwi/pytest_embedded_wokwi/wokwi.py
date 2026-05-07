import json
import logging
import os
import sys
import typing as t
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]

from pytest_embedded.log import DuplicateStdoutPopen, MessageQueue
from pytest_embedded.utils import Meta
from wokwi_client import GET_TOKEN_URL, WokwiClientSync

from .idf import IDFFirmwareResolver

if t.TYPE_CHECKING:  # pragma: no cover
    from pytest_embedded_idf.app import IdfApp


target_to_board = {
    'esp32': 'board-esp32-devkit-c-v4',
    'esp32c3': 'board-esp32-c3-devkitm-1',
    'esp32c5': 'board-esp32-c5-devkitc-1',
    'esp32c6': 'board-esp32-c6-devkitc-1',
    'esp32h2': 'board-esp32-h2-devkitm-1',
    'esp32p4': 'board-esp32-p4-function-ev',
    'esp32s2': 'board-esp32-s2-devkitm-1',
    'esp32s3': 'board-esp32-s3-devkitc-1',
}


class Wokwi(DuplicateStdoutPopen):
    """Synchronous Wokwi integration that inherits from DuplicateStdoutPopen.

    This class provides a synchronous interface to the Wokwi simulator while maintaining
    compatibility with pytest-embedded's logging and message queue infrastructure.
    """

    SOURCE = 'Wokwi'
    REDIRECT_CLS = None  # We'll handle output redirection manually

    def __init__(
        self,
        msg_queue: MessageQueue,
        firmware_resolver: IDFFirmwareResolver,
        wokwi_diagram: str | None = None,
        app: t.Optional['IdfApp'] = None,
        meta: Meta | None = None,
        **kwargs,
    ):
        # Initialize parent class
        super().__init__(msg_queue=msg_queue, meta=meta, **kwargs)

        self.app = app

        # Get Wokwi API token
        token = os.getenv('WOKWI_CLI_TOKEN')
        if not token:
            raise SystemExit(f'Set WOKWI_CLI_TOKEN in your environment. You can get it from {GET_TOKEN_URL}.')

        # Initialize synchronous Wokwi client
        self.client = WokwiClientSync(token)

        # Prepare diagram file if not supplied
        if wokwi_diagram is None:
            self.create_diagram_json()
            wokwi_diagram = os.path.join(self.app.app_path, 'diagram.json')

        # Connect and start simulation
        try:
            firmware_path = Path(firmware_resolver.resolve_firmware(app)).as_posix()
            elf_path = Path(app.elf_file).as_posix()

            self._setup_simulation(wokwi_diagram, firmware_path, elf_path)
            self._start_serial_monitoring()
        except Exception as e:
            self.close()
            raise e

    def _setup_simulation(self, diagram: str, firmware_path: str, elf_path: str):
        """Set up the Wokwi simulation."""
        hello = self.client.connect()
        logging.info('Connected to Wokwi Simulator, server version: %s', hello.get('version', 'unknown'))

        # Upload custom chips before diagram so the server can resolve chip
        # references in the diagram at upload time.
        custom_chips = self._upload_custom_chips(Path(diagram).parent)

        # Upload diagram and ELF
        self.client.upload_file('diagram.json', Path(diagram))
        self.client.upload_file('pytest.elf', Path(elf_path))

        if firmware_path.endswith('flasher_args.json'):
            firmware = self.client.upload_idf_firmware(firmware_path)
            kwargs = {'firmware': firmware.firmware, 'elf': 'pytest.elf', 'flash_size': firmware.flash_size}
        else:
            firmware = self.client.upload_file('pytest.bin', Path(firmware_path))
            kwargs = {'firmware': firmware, 'elf': 'pytest.elf'}

        if custom_chips:
            kwargs['chips'] = custom_chips

        logging.info('Uploaded diagram and firmware to Wokwi. Starting simulation...')
        self.client.start_simulation(**kwargs)

    def _upload_custom_chips(self, diagram_dir: Path) -> list[str]:
        """Upload custom chip files and return chip names.

        Reads chip definitions from ``wokwi.toml`` if present in *diagram_dir*.
        Each ``[[chip]]`` entry must supply a ``name`` and a ``binary`` path
        (relative to the ``wokwi.toml`` file).  When ``wokwi.toml`` is absent
        or contains no chip entries the method falls back to scanning a
        ``chips/`` sub-directory for ``*.chip.json`` / ``*.chip.wasm`` pairs.
        """
        toml_path = diagram_dir / 'wokwi.toml'
        if toml_path.is_file():
            chip_specs = self._chip_specs_from_toml(toml_path)
            if chip_specs is not None:
                return self._upload_chip_specs(chip_specs)

        # Fallback: auto-detect from chips/ directory
        return self._upload_chip_specs(self._chip_specs_from_dir(diagram_dir))

    def _chip_specs_from_toml(
        self, toml_path: Path
    ) -> list[tuple[Path, Path, str]] | None:
        """Parse ``[[chip]]`` entries from *toml_path*.

        All relative paths in the ``[[chip]]`` entries are resolved relative to
        the directory containing *toml_path* (i.e. the sketch directory where
        ``wokwi.toml`` lives), which matches the convention used by the
        ``generate_wokwi_toml`` script.

        Returns a list of ``(json_path, binary_path, chip_name)`` tuples, or
        ``None`` if the file cannot be parsed or contains no chip entries.
        """
        base_dir = toml_path.parent
        try:
            with open(toml_path, 'rb') as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            logging.warning('Could not parse wokwi.toml: %s', e)
            return None

        chip_entries = data.get('chip', [])
        if not chip_entries:
            return None

        specs: list[tuple[Path, Path, str]] = []
        for entry in chip_entries:
            name = entry.get('name')
            binary_rel = entry.get('binary')
            if not name or not binary_rel:
                logging.warning('Skipping chip entry missing name or binary: %s', entry)
                continue

            binary_path = (base_dir / binary_rel).resolve()
            json_path = binary_path.parent / (name + '.chip.json')

            if not binary_path.exists():
                logging.warning('Chip binary not found: %s', binary_path)
                continue
            if not json_path.exists():
                logging.warning('Chip JSON not found: %s', json_path)
                continue

            specs.append((json_path, binary_path, name))

        return specs if specs else None

    def _chip_specs_from_dir(self, diagram_dir: Path) -> list[tuple[Path, Path, str]]:
        """Auto-detect chip specs by scanning ``chips/`` under *diagram_dir*.

        Returns a list of ``(json_path, binary_path, chip_name)`` tuples.
        """
        chips_dir = diagram_dir / 'chips'
        if not chips_dir.is_dir():
            return []

        specs: list[tuple[Path, Path, str]] = []
        for chip_json in chips_dir.glob('*.chip.json'):
            chip_name = chip_json.name.removesuffix('.chip.json')

            chip_binary = None
            for ext in ['.chip.wasm', '.chip.bin']:
                candidate = chips_dir / (chip_name + ext)
                if candidate.exists():
                    chip_binary = candidate
                    break

            if chip_binary is None:
                logging.warning('No binary file found for chip %s, skipping', chip_name)
                continue

            specs.append((chip_json, chip_binary, chip_name))

        return specs

    def _upload_chip_specs(self, specs: list[tuple[Path, Path, str]]) -> list[str]:
        """Upload chip files described by *specs* and return the chip names.

        The Wokwi server requires chip JSON files to be uploaded via the
        ``text`` field of the ``file:upload`` command (not base64-encoded
        binary), matching the behaviour of the official ``wokwi-cli`` TypeScript
        client.  The wokwi-python-client public API only supports binary
        uploads, so we send the JSON via the transport's ``request`` method
        directly.  The binary (``.chip.wasm``) is uploaded normally under its
        original filename.
        """
        chip_names = []
        for json_path, binary_path, chip_name in specs:
            # Send chip JSON as text (server rejects binary-encoded chip JSON).
            self.client._call(
                self.client._async_client._transport.request(
                    'file:upload', {'name': json_path.name, 'text': json_path.read_text(encoding='utf-8')}
                )
            )
            self.client.upload_file(binary_path.name, binary_path)
            chip_names.append(chip_name)
            logging.info('Uploaded custom chip: %s', chip_name)
        return chip_names

    def _start_serial_monitoring(self):
        """Start monitoring serial output and forward to stdout and message queue."""

        def serial_callback(data: bytes):
            # Write to stdout for live monitoring
            try:
                decoded = data.decode('utf-8', errors='replace')
                print(decoded, end='', flush=True)
            except Exception as e:
                logging.debug(f'Error writing to stdout: {e}')

            # Write to log file if available
            try:
                if hasattr(self, '_fw') and self._fw and not self._fw.closed:
                    decoded = data.decode('utf-8', errors='replace')
                    self._fw.write(decoded)
                    self._fw.flush()
            except Exception as e:
                logging.debug(f'Error writing to log file: {e}')

            # Put in message queue for expect() functionality
            try:
                if hasattr(self, '_q') and self._q:
                    self._q.put(data)
            except Exception as e:
                logging.debug(f'Error putting data in message queue: {e}')

        # Start monitoring in background
        self.client.serial_monitor(serial_callback)

    def write(self, s: str | bytes) -> None:
        """Write data to the Wokwi serial interface."""
        try:
            data = s if isinstance(s, bytes) else s.encode('utf-8')
            self.client.serial_write(data)
            logging.debug(f'{self.SOURCE} ->: {s}')
        except Exception as e:
            logging.error(f'Failed to write to Wokwi serial: {e}')

    def close(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'client') and self.client:
                self.client.disconnect()
        except Exception as e:
            logging.debug(f'Error during Wokwi cleanup: {e}')
        finally:
            super().close()

    def __del__(self):
        """Destructor to ensure cleanup when object is garbage collected."""
        self.close()
        super().__del__()

    def terminate(self):
        """Terminate the Wokwi connection."""
        self.close()
        super().terminate()

    def create_diagram_json(self):
        """Create a diagram.json file for the simulation."""
        app = self.app
        target_board = target_to_board[app.target]

        # Check for existing diagram.json file
        diagram_json_path = os.path.join(app.app_path, 'diagram.json')
        if os.path.exists(diagram_json_path):
            with open(diagram_json_path) as f:
                json_data = json.load(f)
            if not any(part['type'] == target_board for part in json_data['parts']):
                logging.warning(
                    f'diagram.json exists, no part with type "{target_board}" found. '
                    + 'You may need to update the diagram.json file manually to match the target board.'
                )
            return

        # Create default diagram
        if app.target == 'esp32p4':
            rx_pin = '38'
            tx_pin = '37'
        else:
            rx_pin = 'RX'
            tx_pin = 'TX'

        diagram = {
            'version': 1,
            'author': 'Uri Shaked',
            'editor': 'wokwi',
            'parts': [{'type': target_board, 'id': 'esp'}],
            'connections': [
                ['esp:' + tx_pin, '$serialMonitor:RX', ''],
                ['esp:' + rx_pin, '$serialMonitor:TX', ''],
            ],
        }

        with open(diagram_json_path, 'w') as f:
            json.dump(diagram, f, indent=2)

    def _hard_reset(self):
        """Fake hard_reset to maintain API consistency."""
        raise NotImplementedError('Hard reset not supported in Wokwi simulation')
