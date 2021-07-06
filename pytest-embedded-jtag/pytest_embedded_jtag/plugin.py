import logging
from types import ModuleType

import pytest

from .dut import JtagDut
from .gdb import Gdb
from .openocd import OpenOcd


def pytest_addoption(parser):
    group = parser.getgroup('embedded')
    group.addoption('--gdb-prog-path', help='GDB program path. (Default: "xtensa-esp32-elf-gdb")')
    group.addoption(
        '--gdb-cli-args',
        help='GDB cli default arguments. Could be overridden by pytest parametrizing. '
        '(Default: "--nx --quiet --interpreter=mi2"',
    )

    group.addoption('--openocd-prog-path', help='openocd program path. (Default: "openocd"')
    group.addoption(
        '--openocd-cli-args',
        help='openocd cli default arguments. Could be overridden by pytest parametrizing. '
        '(Default: "-f board/esp32-wrover-kit-3.3v.cfg -d2"',
    )


@pytest.fixture
def openocd_cli_args(request):
    """
    Apply parametrization to fixture :func:`pytest_embedded_jtag.plugin.openocd`
    """
    return {'openocd_cli_args': getattr(request, 'param', None)}


@pytest.fixture
def openocd(options, openocd_cli_args) -> OpenOcd:
    """
    Uses :attr:`options['OpenOcd']` as kwargs to create instance.

    :return: :class:`pytest_embedded_jtag.openocd.OpenOcd` or derived class instance
    """
    openocd_options = options.get('OpenOcd', {})
    if openocd_cli_args['openocd_cli_args']:
        openocd_options.update(openocd_cli_args)

    openocd = OpenOcd(**openocd_options)
    try:
        yield openocd
    finally:
        openocd.terminate()


@pytest.fixture
def gdb_cli_args(request):
    """
    Apply parametrization to fixture :func:`pytest_embedded_jtag.plugin.gdb`
    """
    return {'gdb_cli_args': getattr(request, 'param', None)}


@pytest.fixture
def gdb(options, gdb_cli_args) -> Gdb:
    """
    Uses :attr:`options['Gdb']` as kwargs to create instance.

    :return: :class:`pytest_embedded_jtag.gdb.Gdb` or derived class instance
    """
    gdb_options = options.get('Gdb', {})
    if gdb_cli_args['gdb_cli_args']:
        gdb_options.update(gdb_cli_args)

    gdb = Gdb(**gdb_options)
    try:
        yield gdb
    finally:
        gdb.terminate()


@pytest.fixture
def dut(serial, openocd, gdb, app, pexpect_proc, options) -> JtagDut:
    """
    Uses :attr:`options['Dut']` as kwargs to create instance.

    :return: :class:`pytest_embedded_jtag.dut.JtagDut` or derived class instance
    """
    dut_options = options.get('Dut', {})
    logging.info(dut_options)
    dut = JtagDut(serial, openocd, gdb, app, pexpect_proc, **dut_options)
    try:
        yield dut
    finally:
        dut.close()


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_embedded.plugin':
        return

    plugin.KNOWN_OPTIONS['OpenOcd'].extend(
        [
            'openocd_prog_path',
            'openocd_cli_args',
        ]
    )

    plugin.KNOWN_OPTIONS['Gdb'].extend(
        [
            'gdb_prog_path',
            'gdb_cli_args',
        ]
    )
