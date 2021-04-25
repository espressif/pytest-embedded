from types import ModuleType

import pytest


def flash(self):
    print('Flashed by jtag')


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_embedded.plugin':
        return

    setattr(plugin.DUT, 'flash', flash)
