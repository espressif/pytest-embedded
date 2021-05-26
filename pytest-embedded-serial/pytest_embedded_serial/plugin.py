from types import ModuleType

import pytest

from .dut import SerialDut


def pytest_addoption(parser):
    group = parser.getgroup('embedded')
    group.addoption('--port', help='serial port')


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_embedded.plugin':
        return

    plugin.KNOWN_OPTIONS['Dut'].append('port')

    setattr(plugin, 'Dut', SerialDut)
