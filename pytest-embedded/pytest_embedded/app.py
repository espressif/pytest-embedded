import os


class App:
    """
    Attributes which could be assigned from Pytest cli should be class attribute
    """

    def __init__(self, app_path: str = os.getcwd(), *args, **kwargs):
        self.app_path = os.path.realpath(app_path)
