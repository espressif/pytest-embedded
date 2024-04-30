import json
import logging
import os
import shutil
import typing as t
from pathlib import Path

import toml
from pytest_embedded import __version__
from pytest_embedded.log import DuplicateStdoutPopen

from .idf import IDFFirmwareResolver

if t.TYPE_CHECKING:
    from pytest_embedded_idf.app import IdfApp


target_to_board = {
    'esp32': 'board-esp32-devkit-c-v4',
    'esp32c3': 'board-esp32-c3-devkitm-1',
    'esp32c6': 'board-esp32-c6-devkitc-1',
    'esp32h2': 'board-esp32-h2-devkitm-1',
    'esp32p4': 'board-esp32-p4-preview',
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
        app: t.Optional['IdfApp'] = None,
        **kwargs,
    ):
        """
        Args:
            wokwi_cli_path: Wokwi CLI arguments
        """
        self.app = app
        self.firmware_resolver = firmware_resolver

        self.create_wokwi_toml()
        self.create_diagram_json()

        wokwi_cli = wokwi_cli_path or self.wokwi_cli_executable
        cmd = [wokwi_cli, '--interactive', app.app_path]
        if (wokwi_timeout is not None) and (wokwi_timeout > 0):
            cmd.extend(['--timeout', str(wokwi_timeout)])
        if (wokwi_scenario is not None) and os.path.exists(wokwi_scenario):
            cmd.extend(['--scenario', wokwi_scenario])

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

        # Check for specific target.diagram.json file first
        diagram_json_path = os.path.join(app.app_path, (app.target + '.diagram.json'))
        if os.path.exists(diagram_json_path):
            # If there is also common diagram.json file, backup it first to diagram.json.old
            if os.path.exists(os.path.join(app.app_path, 'diagram.json')):
                logging.warning(
                    'using %s instead. backup the original diagram.json to diagram.json.old', diagram_json_path
                )
                shutil.copyfile(
                    os.path.join(app.app_path, 'diagram.json'),
                    os.path.join(app.app_path, 'diagram.json.old'),
                )
            # Copy target.diagram.json to diagram.json
            shutil.copyfile(diagram_json_path, os.path.join(app.app_path, 'diagram.json'))
            return

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

        diagram = {
            'version': 1,
            'author': 'Uri Shaked',
            'editor': 'wokwi',
            'parts': [{'type': target_board, 'id': 'esp'}],
            'connections': [
                ['esp:TX', '$serialMonitor:RX', ''],
                ['esp:RX', '$serialMonitor:TX', ''],
            ],
        }
        with open(diagram_json_path, 'w') as f:
            f.write(json.dumps(diagram, indent=2))

    def _hard_reset(self):
        """
        This is a fake hard_reset. Keep this API to keep the consistency.
        """
        raise NotImplementedError
