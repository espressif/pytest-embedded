import json
import logging
import os
import typing as t
from pathlib import Path

from packaging.version import Version
from pytest_embedded.log import DuplicateStdoutPopen, MessageQueue
from pytest_embedded.utils import Meta
from wokwi_client import GET_TOKEN_URL, WokwiClientSync

from pytest_embedded_wokwi import WOKWI_CLI_MINIMUM_VERSION

from .idf import IDFFirmwareResolver

if t.TYPE_CHECKING:  # pragma: no cover
    from pytest_embedded_idf.app import IdfApp


target_to_board = {
    'esp32': 'board-esp32-devkit-c-v4',
    'esp32c3': 'board-esp32-c3-devkitm-1',
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

        # Check version compatibility
        if Version(self.client.version) < Version(WOKWI_CLI_MINIMUM_VERSION):
            logging.warning(
                'Wokwi client version %s < required %s (compatibility not guaranteed)',
                self.client.version,
                WOKWI_CLI_MINIMUM_VERSION,
            )
        logging.info('Wokwi client library version: %s', self.client.version)

        # Prepare diagram file if not supplied
        if wokwi_diagram is None:
            self.create_diagram_json()
            wokwi_diagram = os.path.join(self.app.app_path, 'diagram.json')

        # Connect and start simulation
        try:
            flasher_args = firmware_resolver.resolve_firmware(app)
            firmware_path = Path(flasher_args).as_posix()
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

        # Upload files
        self.client.upload_file('diagram.json', diagram)
        firmware = self.client.upload_file('pytest.bin', firmware_path)

        self.client.upload_file('pytest.elf', elf_path)

        logging.info('Uploaded diagram and firmware to Wokwi. Starting simulation...')

        # Start simulation
        self.client.start_simulation(firmware, elf='pytest.elf')

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
