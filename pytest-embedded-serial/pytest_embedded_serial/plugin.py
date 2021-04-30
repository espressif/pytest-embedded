from types import ModuleType

import pytest

from ._serial import open_port_session


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_embedded.plugin':
        return

    setattr(plugin.DUT, 'open_port_session', open_port_session)
