from types import ModuleType

import pytest


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_idf.plugin':
        return

    setattr(plugin.DUT, 'flash', flash)


def flash(self):
    print('Flashed by serial')
