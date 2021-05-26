from types import ModuleType

import pytest

from .app import IdfApp


def pytest_addoption(parser):
    group = parser.getgroup('embedded')
    group.addoption('--part-tool', help='Partition tool path, used for parsing partition table')


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_embedded.plugin':
        return

    plugin.KNOWN_OPTIONS['App'].append('part_tool')

    setattr(plugin, 'App', IdfApp)

    try:
        from .dut import IdfSerialDut
    except ImportError:
        pass
    else:
        setattr(plugin, 'Dut', IdfSerialDut)
