import os
from typing import Optional


class App:
    """
    Attributes which could be assigned from Pytest cli should be class attribute
    """
    FLASH_ARGS_FILENAME = 'flasher_args.json'

    def __init__(self, app_path: str = os.getcwd(), *args, **kwargs):
        self.app_path = os.path.realpath(app_path)
        self.binary_path = self.get_binary_path()

    def get_binary_path(self) -> Optional[str]:
        path = os.path.join(self.app_path, 'build')

        if path and os.path.exists(path):
            return os.path.realpath(path)
        return None
