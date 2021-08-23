import functools
import importlib
import logging
import os
import sys
from collections import defaultdict, namedtuple
from operator import itemgetter
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest

from .app import App
from .log import DuplicateStdout, PexpectProcess

###########
# helpers #
###########
COUNT = 1


@pytest.fixture(autouse=True)
def count(request):
    """
    Enable parametrization for the same cli option. Inject to global variable.
    """
    global COUNT
    COUNT = _gte_one_int(getattr(request, 'param', request.config.option.count))


def duplicate_count(func) -> Callable[..., Tuple[Optional[str]]]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        option = func(*args, **kwargs)
        if isinstance(option, str):
            res = option.split('|')
        else:
            res = [option]

        if len(res) == 1:
            if COUNT == 1:
                return res[0]
            else:
                return tuple(res * COUNT)
        else:  # len(res) > 1
            if len(res) != COUNT:
                raise ValueError(
                    'The configuration has multi values but the amount is different with the "count" ' 'amount.'
                )
            else:
                return tuple(res)

    return wrapper


def apply_count(func) -> Callable[..., Tuple[Optional[str]]]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if COUNT == 1:
            return func(*args, **kwargs)

        res = tuple()
        for i in range(COUNT):
            getter = itemgetter(i)
            current_kwargs = {}
            for k, v in kwargs.items():
                current_kwargs[k] = getter(v)
            res = tuple(list(res) + [func(*args, **current_kwargs)])

        return res

    return wrapper


def apply_count_generator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        def _close_or_terminate(obj):
            try:
                obj.close()
            except AttributeError:
                try:
                    obj.terminate()
                except AttributeError:
                    del obj

        res = []
        if COUNT == 1:
            res = func(*args, **kwargs)
            try:
                yield res
            finally:
                if res:
                    _close_or_terminate(res)
        else:
            for i in range(COUNT):
                getter = itemgetter(i)
                current_kwargs = {}
                for k, v in kwargs.items():
                    current_kwargs[k] = getter(v)
                res.append(func(*args, **current_kwargs))
            try:
                yield res
            finally:
                for item in res:
                    _close_or_terminate(item)

    return wrapper


####################
# General Fixtures #
####################
@pytest.fixture
def test_file_path(request) -> str:
    """
    Current test script file path
    """
    return request.module.__file__


@pytest.fixture
def test_case_name(request) -> str:
    """
    Current test case function name
    """
    return request.node.originalname


@pytest.fixture
@apply_count_generator
def pexpect_proc() -> PexpectProcess:
    """
    Pre-initialized pexpect process, used for initializing all fixtures who would redirect output
    """
    return PexpectProcess()


@pytest.fixture
@apply_count_generator
def redirect(pexpect_proc) -> Callable[..., DuplicateStdout]:
    """
    Provided a context manager that could help log all the `sys.stdout` with pytest logging feature and redirect
    `sys.stdout` to `dut.pexpect_proc`.

    ```python
    with redirect('prefix'):
        print('this should be logged and sent to pexpect_proc')
    ```
    """

    def _inner(source=None):
        return DuplicateStdout(pexpect_proc, source=source)

    return _inner


#####################
# General Variables #
#####################
BASE_LIB_NAME = 'pytest-embedded'

SERVICE_LIB_NAMES = {
    'serial': f'{BASE_LIB_NAME}-serial',
    'esp': f'{BASE_LIB_NAME}-serial-esp',
    'idf': f'{BASE_LIB_NAME}-idf',
    'jtag': f'{BASE_LIB_NAME}-jtag',
    'qemu': f'{BASE_LIB_NAME}-qemu',
}

FIXTURES_SERVICES = {
    'app': ['base', 'idf', 'qemu'],
    'serial': ['serial', 'esp', 'idf'],
    'openocd': ['jtag'],
    'gdb': ['jtag'],
    'qemu': ['qemu'],
    'dut': ['base', 'serial', 'jtag', 'qemu'],
}


def _gte_one_int(v) -> int:
    try:
        v = int(v)
    except Exception:  # noqa
        pass  # deal with it later
    else:
        if v >= 1:
            return v

    print('"count" value should be a integer greater or equal to 1')
    sys.exit(1)


def pytest_addoption(parser):
    base_group = parser.getgroup('embedded')
    base_group.addoption(
        '--count',
        default=1,
        type=_gte_one_int,
        help='Use this argument when you need multi DUTs in one test case. e.g., master-slave, or mesh.\n'
        'All fixtures would be tuples of instances when this value is more than 1. (Default: 1)\n'
        'Notes:\n'
        'This value should be an integer greater or equal to 1.\n'
        'Use separator "|" for all the other cli options when using different configurations for each DUT.\n'
        'For example:\n'
        '"--embedded-services=esp,idf|esp" for one idf related app and one other type app.\n'
        '"--app-path=test_path1|test_path2" when two DUTs are using different built binary files.\n'
        'The configuration would be duplicated when it has only one value but the "count" amount is '
        'greater than 1. But would raise exception when the configuration has multi values but the amount '
        'is different with the "count" amount.\n',
    )
    base_group.addoption(
        '--embedded-services',
        default='',
        help='Activate comma-separated services for different functionalities.\n'
        'Available services:\n'
        '\tserial: open serial port\n'
        '\tesp: auto-detect target/port by esptool\n'
        '\tidf: auto-detect more app info with idf specific rules, auto flash-in\n'
        '\tjtag: openocd and gdb\n'
        '\tqemu: use qemu simulator\n',
    )
    base_group.addoption('--app-path', help='App path')

    serial_group = parser.getgroup('embedded-serial')
    serial_group.addoption('--port', help='serial port. Could be overridden by pytest parametrizing. (Default: "None")')

    esp_group = parser.getgroup('embedded-esp')
    esp_group.addoption(
        '--target', help='serial target chip type. Could be overridden by pytest parametrizing. (Default: "auto")'
    )

    idf_group = parser.getgroup('embedded-idf')
    idf_group.addoption(
        '--part-tool',
        help='Partition tool path, used for parsing partition table. '
        '(Default: "$IDF_PATH/components/partition_table/gen_esp32part.py"',
    )

    jtag_group = parser.getgroup('embedded-jtag')
    jtag_group.addoption('--gdb-prog-path', help='GDB program path. (Default: "xtensa-esp32-elf-gdb")')
    jtag_group.addoption(
        '--gdb-cli-args',
        help='GDB cli arguments. Could be overridden by pytest parametrizing. '
        '(Default: "--nx --quiet --interpreter=mi2"',
    )
    jtag_group.addoption('--openocd-prog-path', help='openocd program path. (Default: "openocd"')
    jtag_group.addoption(
        '--openocd-cli-args',
        help='openocd cli arguments. Could be overridden by pytest parametrizing. '
        '(Default: f board/esp32-wrover-kit-3.3v.cfg -d2"',
    )

    qemu_group = parser.getgroup('embedded-qemu')
    qemu_group.addoption(
        '--qemu-image-path',
        help='QEMU image path. Could be overridden by pytest parametrizing. (Default: "<app_path>/flash_image.bin)',
    )
    qemu_group.addoption(
        '--qemu-prog-path',
        help='QEMU program path. (Default: "qemu-system-xtensa")',
    )
    qemu_group.addoption(
        '--qemu-cli-args',
        help='QEMU cli default arguments. Could be overridden by pytest parametrizing. '
        '(Default: "-nographic -no-reboot -machine esp32")',
    )
    qemu_group.addoption(
        '--qemu-extra-args',
        help='QEMU cli extra arguments, will append to the argument list. '
        'Could be overridden by pytest parametrizing. (Default: None)',
    )
    qemu_group.addoption(
        '--qemu-log-path',
        help='QEMU log file path. (Default: "<temp folder>/<timestamp>/serial.log")',
    )


###############################
# CLI Option Related Fixtures #
###############################
########
# base #
########
@pytest.fixture
@duplicate_count
def embedded_services(request) -> Optional[str]:
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('embedded_services')


@pytest.fixture
@duplicate_count
def app_path(request) -> Optional[str]:
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('app_path')


##########
# serial #
##########
@pytest.fixture
@duplicate_count
def port(request) -> Optional[str]:
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('port')


#######
# esp #
#######
@pytest.fixture
@duplicate_count
def target(request) -> Optional[str]:
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('target')


#######
# idf #
#######
@pytest.fixture
@duplicate_count
def part_tool(request) -> Optional[str]:
    return getattr(request, 'param', None) or request.config.option.__dict__.get('part_tool')


########
# jtag #
########
@pytest.fixture
@duplicate_count
def gdb_prog_path(request):
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('gdb_prog_path')


@pytest.fixture
@duplicate_count
def gdb_cli_args(request):
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('gdb_cli_args')


@pytest.fixture
@duplicate_count
def openocd_prog_path(request):
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('openocd_prog_path')


@pytest.fixture
@duplicate_count
def openocd_cli_args(request):
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('openocd_cli_args')


########
# qemu #
########
@pytest.fixture
@duplicate_count
def qemu_image_path(request):
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('qemu_image_path')


@pytest.fixture
@duplicate_count
def qemu_prog_path(request):
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('qemu_prog_path')


@pytest.fixture
@duplicate_count
def qemu_cli_args(request):
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('qemu_cli_args')


@pytest.fixture
@duplicate_count
def qemu_extra_args(request):
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('qemu_extra_args')


@pytest.fixture
@duplicate_count
def qemu_log_path(request):
    """
    Enable parametrization for the same cli option
    """
    return getattr(request, 'param', None) or request.config.option.__dict__.get('qemu_log_path')


####################
# Private Fixtures #
####################
@pytest.fixture
@apply_count
def _services(embedded_services) -> List[str]:
    services = [s for s in embedded_services.split(',') if s]

    for s in services:
        if s not in SERVICE_LIB_NAMES.keys():
            raise ValueError('service "s" not available, please run "--help" for more information')

        try:
            importlib.import_module(SERVICE_LIB_NAMES[s].replace('-', '_'))
        except ModuleNotFoundError:
            logging.error(f'Please install {SERVICE_LIB_NAMES[s]} to enable service {s}')
            sys.exit(1)

    return ['base'] + services


ClassCliOptions = namedtuple('cls_kwargs', ['classes', 'kwargs'])  # Tuple[Dict[str, type], Dict[str, list[str]]]


@pytest.fixture
@apply_count
def _fixture_classes_and_options(
    _services,
    # parametrize fixtures
    app_path,
    port,
    target,
    part_tool,
    openocd_prog_path,
    openocd_cli_args,
    gdb_prog_path,
    gdb_cli_args,
    qemu_image_path,
    qemu_prog_path,
    qemu_cli_args,
    qemu_extra_args,
    qemu_log_path,
    # pre-initialized fixtures
    pexpect_proc,
) -> ClassCliOptions:
    classes = {}
    kwargs = defaultdict(dict)  # type: Dict[str, Dict[str, Any]]  # For store options for each fixtures

    for fixture, provide_services in FIXTURES_SERVICES.items():
        if fixture == 'app':
            kwargs['app'] = {'app_path': app_path}
            if 'idf' in _services:
                if 'qemu' in _services:
                    from pytest_embedded_qemu.app import QemuApp, DEFAULT_IMAGE_FN

                    classes[fixture] = QemuApp
                    kwargs[fixture].update(
                        {
                            'part_tool': part_tool,
                            'qemu_image_path': (qemu_image_path or os.path.join(app_path or '', DEFAULT_IMAGE_FN)),
                            'pexpect_proc': pexpect_proc,
                        }
                    )
                else:
                    from pytest_embedded_idf.app import IdfApp

                    classes[fixture] = IdfApp
                    kwargs[fixture].update(
                        {
                            'part_tool': part_tool,
                            'pexpect_proc': pexpect_proc,
                        }
                    )
            else:
                from .app import App

                classes[fixture] = App
        elif fixture == 'serial':
            if 'esp' in _services:
                kwargs[fixture] = {
                    'target': target,
                    'port': port,
                    'pexpect_proc': pexpect_proc,
                }
                if 'idf' in _services:
                    from pytest_embedded_idf.serial import IdfSerial

                    classes[fixture] = IdfSerial
                    kwargs[fixture].update(
                        {
                            'app': None,
                        }
                    )
                else:
                    from pytest_embedded_serial_esp.serial import EspSerial

                    classes[fixture] = EspSerial
            elif 'serial' in _services or 'jtag' in _services:
                from pytest_embedded_serial.serial import Serial

                classes[fixture] = Serial
                kwargs[fixture] = {
                    'port': port,
                    'pexpect_proc': pexpect_proc,
                }
        elif fixture in ['openocd', 'gdb']:
            if 'jtag' in _services:
                if fixture == 'openocd':
                    from pytest_embedded_jtag.openocd import OpenOcd

                    classes[fixture] = OpenOcd
                    kwargs[fixture] = {
                        'openocd_prog_path': openocd_prog_path,
                        'openocd_cli_args': openocd_cli_args,
                    }
                else:
                    from pytest_embedded_jtag.gdb import Gdb

                    classes[fixture] = Gdb
                    kwargs[fixture] = {
                        'gdb_prog_path': gdb_prog_path,
                        'gdb_cli_args': gdb_cli_args,
                    }
        elif fixture == 'qemu':
            if 'qemu' in _services:
                from pytest_embedded_qemu.qemu import Qemu
                from pytest_embedded_qemu.app import DEFAULT_IMAGE_FN

                classes[fixture] = Qemu
                kwargs[fixture] = {
                    'qemu_image_path': (qemu_image_path or os.path.join(app_path or '', DEFAULT_IMAGE_FN)),
                    'qemu_prog_path': qemu_prog_path,
                    'qemu_cli_args': qemu_cli_args,
                    'qemu_extra_args': qemu_extra_args,
                    'qemu_log_path': qemu_log_path,
                }
        elif fixture == 'dut':
            kwargs[fixture] = {
                'app': None,
                'pexpect_proc': pexpect_proc,
            }
            if 'qemu' in _services:
                from pytest_embedded_qemu.dut import QemuDut

                classes[fixture] = QemuDut
                kwargs[fixture].update(
                    {
                        'qemu': None,
                    }
                )
            elif 'jtag' in _services:
                from pytest_embedded_jtag.dut import JtagDut

                classes[fixture] = JtagDut
                kwargs[fixture].update(
                    {
                        'serial': None,
                        'openocd': None,
                        'gdb': None,
                    }
                )
            elif 'serial' in _services or 'esp' in _services:
                from pytest_embedded_serial.dut import SerialDut

                classes[fixture] = SerialDut
                kwargs[fixture].update(
                    {
                        'serial': None,
                    }
                )
            else:
                from .dut import Dut

                classes[fixture] = Dut

    return ClassCliOptions(classes, kwargs)


####################
# Derived Fixtures #
####################
@pytest.fixture
@apply_count
def app(_fixture_classes_and_options) -> App:
    """
    A pytest fixture to gather information from the specified built binary folder
    """
    cls = _fixture_classes_and_options.classes['app']
    kwargs = _fixture_classes_and_options.kwargs['app']
    return cls(**kwargs)


@pytest.fixture
@apply_count_generator
def serial(_fixture_classes_and_options, app):
    """
    A serial subprocess which could read/redirect/write
    """
    if 'serial' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['serial']
    kwargs = _fixture_classes_and_options.kwargs['serial']
    if 'app' in kwargs and kwargs['app'] is None:
        kwargs['app'] = app
    return cls(**kwargs)


@pytest.fixture
@apply_count_generator
def openocd(_fixture_classes_and_options):
    """
    A openocd subprocess which could read/redirect/write
    """
    if 'openocd' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['openocd']
    kwargs = _fixture_classes_and_options.kwargs['openocd']
    return cls(**kwargs)


@pytest.fixture
@apply_count_generator
def gdb(_fixture_classes_and_options):
    """
    A gdb subprocess which could read/redirect/write
    """
    if 'gdb' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['gdb']
    kwargs = _fixture_classes_and_options.kwargs['gdb']
    return cls(**kwargs)


@pytest.fixture
@apply_count_generator
def qemu(_fixture_classes_and_options):
    """
    A qemu subprocess which could read/redirect/write
    """
    if 'qemu' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['qemu']
    kwargs = _fixture_classes_and_options.kwargs['qemu']
    return cls(**kwargs)


@pytest.fixture
@apply_count_generator
def dut(_fixture_classes_and_options, app, serial, openocd, gdb, qemu):
    """
    A device under test (DUT) object which could gather output from various sources and redirect them to the pexpect
    process.
    """
    cls = _fixture_classes_and_options.classes['dut']
    kwargs = _fixture_classes_and_options.kwargs['dut']

    for k, v in kwargs.items():
        if v is None:
            if k == 'app':
                kwargs[k] = app
            elif k == 'serial':
                kwargs[k] = serial
            elif k == 'openocd':
                kwargs[k] = openocd
            elif k == 'gdb':
                kwargs[k] = gdb
            elif k == 'qemu':
                kwargs[k] = qemu
    return cls(**kwargs)
