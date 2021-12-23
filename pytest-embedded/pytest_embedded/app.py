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
        self.build_dir = build_dir or 'build'

        for k, v in kwargs.items():
            setattr(self, k, v)
