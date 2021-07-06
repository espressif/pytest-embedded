import logging
import os
from types import ModuleType

import pytest
from pytest_embedded_qemu import DEFAULT_IMAGE_FN

from .dut import QemuDut
from .qemu import Qemu


def pytest_addoption(parser):
    group = parser.getgroup('embedded')
    group.addoption(
        '--qemu-image-path',
        help='QEMU image path. Could be overridden by pytest parametrizing. ' '(Default: "<app_path>/flash_image.bin)',
    )
    group.addoption(
        '--qemu-prog-path',
        help='QEMU program path. (Default: "qemu-system-xtensa")',
    )
    group.addoption(
        '--qemu-cli-args',
        help='QEMU cli default arguments. Could be overridden by pytest parametrizing. '
        '(Default: "-nographic -no-reboot -machine esp32")',
    )
    group.addoption(
        '--qemu-extra-args',
        help='QEMU cli extra arguments, will append to the argument list. '
        'Could be overridden by pytest parametrizing. (Default: None)',
    )
    group.addoption(
        '--qemu-log-path',
        help='QEMU log file path. (Default: "<temp folder>/<timestamp>/serial.log")',
    )


@pytest.fixture
def qemu_image_path(request):
    return {'qemu_image_path': getattr(request, 'param', None)}


@pytest.fixture
def qemu_cli_args(request):
    """
    Apply parametrization to fixture :func:`pytest_embedded_qemu_idf.plugin.qemu`
    """
    return {'qemu_cli_args': getattr(request, 'param', None)}


@pytest.fixture
def qemu_extra_args(request):
    """
    Apply parametrization to fixture :func:`pytest_embedded_qemu_idf.plugin.qemu`
    """
    return {'qemu_extra_args': getattr(request, 'param', None)}


@pytest.hookimpl
def pytest_plugin_registered(plugin, manager):
    if not isinstance(plugin, ModuleType) or plugin.__name__ != 'pytest_embedded.plugin':
        return

    plugin.KNOWN_OPTIONS['Qemu'].extend(
        [
            'qemu_image_path',
            'qemu_prog_path',
            'qemu_cli_args',
            'qemu_extra_args',
            'qemu_log_path',
        ]
    )
    plugin.ENV['qemu'] = True

    if 'idf' in plugin.ENV:
        from .app import QemuApp

        plugin.KNOWN_OPTIONS['App'].append('qemu_image_path')

        @pytest.fixture
        def app(qemu_image_path, pexpect_proc, options, test_file_path) -> QemuApp:
            """
            Uses :attr:`options['App']` as kwargs to create instance.

            :return: :class:`pytest_embedded.app.App` or derived class instance
            """
            app_options = options.get('App', {})
            if app_options['app_path'] is None:
                logging.info(f'test_file_path: {test_file_path}')
                app_path = os.path.dirname(test_file_path)
            else:
                app_path = app_options['app_path']
            app_options['app_path'] = app_path

            if qemu_image_path['qemu_image_path']:
                app_options.update(qemu_image_path)

            if app_options['qemu_image_path'] is None:
                app_options['qemu_image_path'] = os.path.join(app_path, DEFAULT_IMAGE_FN)

            app_options['pexpect_proc'] = pexpect_proc
            return QemuApp(**app_options)

        globals()['app'] = app

    @pytest.fixture
    def qemu(app, options, qemu_image_path, qemu_cli_args, qemu_extra_args) -> Qemu:
        """
        Uses :attr:`options['Qemu']` as kwargs to create instance.

        :return: :class:`pytest_embedded_qemu_idf.qemu.IdfQemu` or derived class instance
        """
        qemu_options = options.get('Qemu', {})
        if qemu_image_path['qemu_image_path']:
            qemu_options.update(qemu_image_path)
        if qemu_cli_args['qemu_cli_args']:
            qemu_options.update(qemu_cli_args)
        if qemu_extra_args['qemu_extra_args']:
            qemu_options.update(qemu_extra_args)

        if qemu_options['qemu_image_path'] is None:
            qemu_options['qemu_image_path'] = os.path.join(app.app_path, DEFAULT_IMAGE_FN)

        qemu = Qemu(**qemu_options)
        try:
            yield qemu
        finally:
            qemu.close()

    globals()['qemu'] = qemu

    @pytest.fixture
    def dut(qemu, app, pexpect_proc, options) -> QemuDut:
        """
        Uses :attr:`options['Dut']` as kwargs to create instance.

        :return: :class:`pytest_embedded_qemu_idf.dut.QemuDut` or derived class instance
        """
        dut_options = options.get('Dut', {})
        dut = QemuDut(qemu, app, pexpect_proc, **dut_options)
        try:
            yield dut
        finally:
            dut.close()

    globals()['dut'] = dut
