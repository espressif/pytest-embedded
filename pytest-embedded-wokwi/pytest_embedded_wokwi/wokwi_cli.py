import json
import logging
import os
import re
import shutil
import subprocess
import typing as t
from pathlib import Path

import toml
from packaging.version import Version
from pytest_embedded import __version__
from pytest_embedded.log import DuplicateStdoutPopen

from pytest_embedded_wokwi import WOKWI_CLI_MINIMUM_VERSION

from .idf import IDFFirmwareResolver

if t.TYPE_CHECKING:
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


class WokwiCLI(DuplicateStdoutPopen):
    """
    WokwiCLI class
    """

    SOURCE = 'Wokwi'
    WOKWI_CLI_PATH = 'wokwi-cli'

    def __init__(
        self,
        firmware_resolver: IDFFirmwareResolver,
        wokwi_cli_path: t.Optional[str] = None,
        wokwi_timeout: t.Optional[int] = None,
        wokwi_scenario: t.Optional[str] = None,
        wokwi_diagram: t.Optional[str] = None,
        app: t.Optional['IdfApp'] = None,
        **kwargs,
    ):
        """
        Args:
            wokwi_cli_path: Wokwi CLI arguments
        """
        self.app = app
        self.firmware_resolver = firmware_resolver

        # first need to check if wokwi-cli exists in PATH
        if shutil.which('wokwi-cli') is None:
            raise RuntimeError('Please install wokwi-cli, by running: curl -L https://wokwi.com/ci/install.sh | sh')

        output = subprocess.check_output(['wokwi-cli', '--help'])
        try:
            wokwi_cli_version = re.match(r'Wokwi CLI v(\d+\.\d+\.\d+)', output.decode('utf-8')).group(1)
        except AttributeError:
            logging.warning('Failed to get wokwi-cli version, assume version requirements satisfied')
        else:
            if Version(wokwi_cli_version) < Version(WOKWI_CLI_MINIMUM_VERSION):
                raise ValueError(
                    f'Wokwi CLI version {wokwi_cli_version} is not supported. '
                    f'Minimum version required: {WOKWI_CLI_MINIMUM_VERSION}. '
                    f'To update Wokwi CLI run: curl -L https://wokwi.com/ci/install.sh | sh'
                )

        self.create_wokwi_toml()

        if wokwi_diagram is None:
            self.create_diagram_json()

        wokwi_cli = wokwi_cli_path or self.wokwi_cli_executable
        cmd = [wokwi_cli, '--interactive', app.app_path]
        if (wokwi_timeout is not None) and (wokwi_timeout > 0):
            cmd.extend(['--timeout', str(wokwi_timeout)])
        if (wokwi_scenario is not None) and os.path.exists(wokwi_scenario):
            cmd.extend(['--scenario', wokwi_scenario])
        if (wokwi_diagram is not None) and os.path.exists(wokwi_diagram):
            cmd.extend(['--diagram-file', wokwi_diagram])

        super().__init__(
            cmd=cmd,
            **kwargs,
        )

    @property
    def wokwi_cli_executable(self):
        return self.WOKWI_CLI_PATH

    def create_wokwi_toml(self):
        app = self.app
        flasher_args = self.firmware_resolver.resolve_firmware(app)
        wokwi_toml_path = os.path.join(app.app_path, 'wokwi.toml')
        firmware_path = Path(os.path.relpath(flasher_args, app.app_path)).as_posix()
        elf_path = Path(os.path.relpath(app.elf_file, app.app_path)).as_posix()

        if os.path.exists(wokwi_toml_path):
            with open(wokwi_toml_path) as f:
                toml_data = toml.load(f)

            if 'wokwi' not in toml_data:
                toml_data['wokwi'] = {'version': 1}

            wokwi_table = toml_data['wokwi']
            if wokwi_table.get('firmware') == firmware_path and wokwi_table.get('elf') == elf_path:
                # No need to update
                return

            wokwi_table.update({'firmware': firmware_path, 'elf': elf_path})
        else:
            toml_data = {
                'wokwi': {
                    'version': 1,
                    'generatedBy': f'pytest-embedded-wokwi {__version__}',
                    'firmware': firmware_path,
                    'elf': elf_path,
                }
            }

        with open(wokwi_toml_path, 'w') as f:
            toml.dump(toml_data, f)

    def create_diagram_json(self):
        app = self.app
        target_board = target_to_board[app.target]

        # Check for common diagram.json file
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
            f.write(json.dumps(diagram, indent=2))

    def _hard_reset(self):
        """
        This is a fake hard_reset. Keep this API to keep the consistency.
        """
        raise NotImplementedError
