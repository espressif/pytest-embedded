import typing as t
from pathlib import Path

if t.TYPE_CHECKING:
    from pytest_embedded_idf.app import IdfApp


class IDFFirmwareResolver:
    """
    IDFFirmwareResolver class
    """

    def resolve_firmware(self, app: 'IdfApp'):
        return Path(app.binary_path, 'flasher_args.json')
