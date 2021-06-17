import logging
from types import ModuleType

import pytest

from .dut import SerialDut


def pytest_addoption(parser):
    group = parser.getgroup('embedded')
    group.addoption('--port', help='serial port. Could be overridden by pytest parametrizing. (Default: "auto")')


@pytest.fixture
def port(request):
    """
    Apply parametrization to fixture :func:`pytest_embedded_serial.plugin.dut`
    """
    return {'port': getattr(request, 'param', None)}


@pytest.fixture
def dut(port, app, options) -> SerialDut:
    """
    Uses :attr:`options['Dut']` as kwargs to create instance.

    :return: :class:`pytest_embedded.dut.Dut` or derived class instance
    """
    dut_options = options.get('Dut', {})
    if port['port']:
        dut_options.update(port)
    logging.info(dut_options)
    dut = SerialDut(app=app, **dut_options)
    try:
        yield dut
    finally:
        dut.close()


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_embedded.plugin':
        return

    plugin.KNOWN_OPTIONS['Dut'].append('port')
