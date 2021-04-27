from .app import App


class DUT:
    def __init__(self, app: App) -> None:
        self.app = app
