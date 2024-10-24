import typing as t
from pathlib import Path

if t.TYPE_CHECKING:
    from pytest_embedded_arduino.app import ArduinoApp


class ArduinoFirmwareResolver:
    """
    ArduinoFirmwareResolver class
    """

    def resolve_firmware(self, app: 'ArduinoApp'):
        # get path of ino.bin file
        return Path(app.binary_path, app.sketch + '.ino.merged.bin')
