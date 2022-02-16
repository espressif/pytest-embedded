import logging
import os
from typing import Optional


class App:
    """
    Built binary files base class
    """

    def __init__(
        self,
        app_path: Optional[str] = None,
        build_dir: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            app_path: App path
            build_dir: Build directory (where binaries reside)
        """
        if app_path is None:
            app_path = os.getcwd()

        self.app_path = os.path.realpath(app_path)
        self.build_dir = build_dir
        self.binary_path = self._get_binary_path()

        for k, v in kwargs.items():
            setattr(self, k, v)

    def _get_binary_path(self) -> Optional[str]:
        if not self.build_dir:
            return None

        if os.path.isdir(self.build_dir):
            return os.path.realpath(self.build_dir)

        logging.debug(f'{self.build_dir} doesn\'t exist. Treat it as a relative path...')
        path = os.path.join(self.app_path, self.build_dir)
        if os.path.isdir(path):
            return path

        logging.debug(f'{path} doesn\'t exist.')
        return None
