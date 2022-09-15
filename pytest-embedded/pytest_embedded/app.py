import logging
import os
from typing import Optional


class App:
    """
    Built binary files base class

    Attributes:
        app_path (str): application folder path
        binary_path (str): binary folder path
    """

    def __init__(
        self,
        app_path: Optional[str] = None,
        build_dir: Optional[str] = None,
        **kwargs,
    ):
        if app_path is None:
            app_path = os.getcwd()

        self.app_path = os.path.realpath(app_path)
        self.binary_path = self._get_binary_path(build_dir)

        for k, v in kwargs.items():
            setattr(self, k, v)

    def _get_binary_path(self, build_dir: Optional[str] = None) -> Optional[str]:
        if not build_dir:
            return None

        if os.path.isdir(build_dir):
            return os.path.realpath(build_dir)

        logging.debug(f'{build_dir} doesn\'t exist. Treat it as a relative path...')
        path = os.path.join(self.app_path, build_dir)
        if os.path.isdir(path):
            return path

        logging.debug(f'{path} doesn\'t exist.')
        return None
