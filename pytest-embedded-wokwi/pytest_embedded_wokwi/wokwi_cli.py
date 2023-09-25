import json
import os
import typing as t

from pytest_embedded import __version__
from pytest_embedded.log import DuplicateStdoutPopen

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
        wokwi_cli_path: t.Optional[str] = None,
        app: t.Optional['IdfApp'] = None,
        **kwargs,
    ):
        """
        Args:
            wokwi_cli_path: Wokwi CLI arguments
        """
        self.app = app

        bin_list = []
        app_binary = None
        for file in app.flash_files:
            if not os.path.exists(file.file_path):
                raise ValueError(f'Firmware binary file doesn\'t exist: {file.file_path}')
            file_rel_path = os.path.relpath(app.elf_file, app.app_path)
            bin_list.append(f"'{file.offset:#x} {file_rel_path}',")
            # The following is a workaround until wokwi-cli supports multiple binaries
            if file.offset == 0x10000:
                app_binary = file_rel_path

        bin_list_toml = '\n  '.join(bin_list)
        with open(os.path.join(app.app_path, 'wokwi.toml'), 'wt') as f:
            f.write(
                f"""
[wokwi]
version = 1
generatedBy = 'pytest-embedded-wokwi {__version__}'
firmware = '{app_binary}'
elf = '{os.path.relpath(app.elf_file, app.app_path)}'

# We don't support multiple binaries yet, so this will be ignored for now:
flash = [
  {bin_list_toml}
]
"""
            )

        # TODO: Check if diagram already exist and update it?
        diagram = {
            'version': 1,
            'author': 'Uri Shaked',
            'editor': 'wokwi',
            'parts': [{'type': target_to_board[app.target], 'id': 'esp'}],
            'connections': [
                ['esp:TX', '$serialMonitor:RX', '', []],
                ['esp:RX', '$serialMonitor:TX', '', []],
            ],
        }
        with open(os.path.join(app.app_path, 'diagram.json'), 'wt') as f:
            f.write(json.dumps(diagram))

        wokwi_cli = wokwi_cli_path or self.wokwi_cli_executable

        super().__init__(
            cmd=[wokwi_cli, app.app_path],
            **kwargs,
        )

    @property
    def wokwi_cli_executable(self):
        return self.WOKWI_CLI_PATH

    def _hard_reset(self):
        """
        This is a fake hard_reset. Keep this API to keep the consistency.
        """
        raise NotImplementedError
