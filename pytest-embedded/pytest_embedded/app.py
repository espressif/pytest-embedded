import os
from typing import Optional


class App:
    """
    Built binary files base class
    """

    def __init__(self, app_path: Optional[str] = None, **kwargs):
        """
        Args:
            app_path: App path
        """
        if app_path is None:
            app_path = os.getcwd()
        self.app_path = os.path.realpath(app_path)

        for k, v in kwargs.items():
            setattr(self, k, v)
