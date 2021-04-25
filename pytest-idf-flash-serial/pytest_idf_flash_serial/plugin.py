from types import ModuleType

import pytest


def flash(self):
    print('Flashed by serial')


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_idf_base.plugin':
        return

    setattr(plugin.DUT, 'flash', flash)
