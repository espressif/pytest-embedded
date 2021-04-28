from types import ModuleType

import pytest

from ._serial import get_raw_output_io


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_embedded.plugin':
        return

    setattr(plugin.DUT, 'get_raw_output_io', get_raw_output_io)
