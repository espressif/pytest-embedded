import json
import logging
import os
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

        super().__init__(
            cmd=[wokwi_cli, app.app_path],
            **kwargs,
        )

    @property
    def wokwi_cli_executable(self):
        return self.WOKWI_CLI_PATH

    def create_wokwi_toml(self):
        app = self.app
        flasher_args = self.firmware_resolver.resolve_firmware(app)
        wokwi_toml_path = os.path.join(app.app_path, 'wokwi.toml')
        firmware_path = Path(flasher_args).relative_to(app.app_path).as_posix()
        elf_path = Path(app.elf_file).relative_to(app.app_path).as_posix()

        if os.path.exists(wokwi_toml_path):
            with open(wokwi_toml_path, 'rt') as f:
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

        with open(wokwi_toml_path, 'wt') as f:
            toml.dump(toml_data, f)

    def create_diagram_json(self):
        app = self.app
        diagram_json_path = os.path.join(app.app_path, 'diagram.json')
        target_board = target_to_board[app.target]

        if os.path.exists(diagram_json_path):
            with open(diagram_json_path, 'rt') as f:
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
        with open(diagram_json_path, 'wt') as f:
            f.write(json.dumps(diagram, indent=2))

    def _hard_reset(self):
        """
        This is a fake hard_reset. Keep this API to keep the consistency.
        """
        raise NotImplementedError
