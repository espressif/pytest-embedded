from types import ModuleType

import pytest

from .dut import IdfQemuDut


def pytest_addoption(parser):
    group = parser.getgroup('embedded')
    group.addoption(
        '--qemu-prog',
        help='QEMU program path, "qemu-system-xtensa" would be used if not set',
    )
    group.addoption(
        '--qemu-extra-args',
        help='QEMU cli extra arguments, "-nographic -no-reboot -machine esp32" would be used if not set',
    )


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_embedded.plugin':
        return

    plugin.KNOWN_OPTIONS['Dut'].append('qemu_prog')

    setattr(plugin, 'Dut', IdfQemuDut)
