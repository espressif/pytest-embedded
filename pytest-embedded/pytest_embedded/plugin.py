import datetime
import functools
import importlib
import logging
import os
import sys
import tempfile
from collections import defaultdict, namedtuple
from operator import itemgetter
from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

import pytest
from _pytest.config import Config
from _pytest.fixtures import (
    FixtureDef,
    FixtureRequest,
    SubRequest,
    call_fixture_func,
    resolve_fixture_function,
)
from _pytest.main import Session
from _pytest.outcomes import TEST_OUTCOME
from _pytest.python import Function

from .app import App
from .dut import Dut
from .log import DuplicateStdout, PexpectProcess
from .unity import JunitMerger
from .utils import find_by_suffix, to_list

if TYPE_CHECKING:
    from pytest_embedded_jtag.gdb import Gdb
    from pytest_embedded_jtag.openocd import OpenOcd
    from pytest_embedded_qemu.qemu import Qemu
    from pytest_embedded_serial.serial import Serial


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
        '"--embedded-services=esp,idf|esp" for one idf related app and one other type of app.\n'
        '"--app-path=test_path1|test_path2" when two DUTs are using different built binary files.\n'
        '"--part-tool=part_tool_path|" when only the first DUT needs this option, '
        'the second should keep as empty.\n'
        '"--embedded-services=idf --count=2" when both of these DUTs are using the same services.\n'
        'The configuration would be duplicated when it has only one value but the "count" amount is '
        'greater than 1. It would raise an exception when the configuration has multi values but the amount '
        'is different from the "count" amount.\n'
        'For example:\n'
        '"--embedded-services=idf|esp-idf --count=3" would raise an exception.',
    )
    base_group.addoption(
        '--parallel-count', default=1, type=_gte_one_int, help='Number of parallel build jobs. (Default: 1)'
    )
    base_group.addoption(
        '--parallel-index',
        default=1,
        type=_gte_one_int,
        help='Index (1-based) of the job, out of the number specified by --parallel-count. (Default: 1)',
    )
    base_group.addoption(
        '--embedded-services',
        default='',
        help='Activate comma-separated services for different functionalities. (Default: "")\n'
        'Available services:\n'
        '- serial: open serial port\n'
        '- esp: auto-detect target/port by esptool\n'
        '- idf: auto-detect more app info with idf specific rules, auto flash-in\n'
        '- jtag: openocd and gdb\n'
        '- qemu: use qemu simulator instead of the real target\n'
        '- arduino: auto-detect more app info with arduino specific rules, auto flash-in\n'
        'All the related CLI options are under the groups named by "embedded-<service>"',
    )
    base_group.addoption('--app-path', help='App path')
    base_group.addoption('--build-dir', help='build directory under the app_path. (Default: "build")')
    base_group.addoption(
        '--with-timestamp',
        help='y/yes/true for True and n/no/false for False. '
        'Set to True to enable print with timestamp. (Default: True)',
    )
    base_group.addoption(
        '--reorder-by-app-path',
        action='store_true',
        help='Reorder the test sequence according to the [app_path] and [build_dir]. (Default: False)',
    )

    serial_group = parser.getgroup('embedded-serial')
    serial_group.addoption('--port', help='serial port. (Env: "ESPPORT" if service "esp" specified, Default: "None")')

    esp_group = parser.getgroup('embedded-esp')
    esp_group.addoption('--target', help='serial target chip type. (Default: "auto")')
    esp_group.addoption('--baud', help='serial port baud rate used when flashing. (Env: "ESPBAUD", Default: 115200)')
    esp_group.addoption(
        '--skip-autoflash',
        help='y/yes/true for True and n/no/false for False. Set to True to disable auto flash. (Default: False)',
    )

    idf_group = parser.getgroup('embedded-idf')
    idf_group.addoption(
        '--part-tool',
        help='Partition tool path, used for parsing partition table. '
        '(Default: "$IDF_PATH/components/partition_table/gen_esp32part.py"',
    )
    idf_group.addoption(
        '--confirm-target-elf-sha256',
        help='y/yes/true for True and n/no/false for False. '
        'Set to True to read the elf sha256 from target flash and compare to the local elf under '
        'app.binary_path when session target-app cache decide to skip the autoflash. (Default: False)',
    )
    idf_group.addoption(
        '--erase-nvs',
        help='y/yes/true for True and n/no/false for False. '
        'Set to True to erase the non-volatile storage blocks when flash files to the target chip. '
        'Requires valid partition tool. (Default: False)',
    )
    idf_group.addoption(
        '--skip-check-coredump',
        help='y/yes/true for True and n/no/false for False. '
        'Set to True to skip auto check core dump in UART/flash while teardown the failing test case. '
        'Requires valid partition tool, project_description.json under the build dir. (Default: False)',
    )

    jtag_group = parser.getgroup('embedded-jtag')
    jtag_group.addoption('--gdb-prog-path', help='GDB program path. (Default: "xtensa-esp32-elf-gdb")')
    jtag_group.addoption(
        '--gdb-cli-args',
        help='GDB cli arguments. (Default: "--nx --quiet --interpreter=mi2"',
    )
    jtag_group.addoption('--openocd-prog-path', help='openocd program path. (Default: "openocd")')
    jtag_group.addoption(
        '--openocd-cli-args',
        help='openocd cli arguments. (Default: "f board/esp32-wrover-kit-3.3v.cfg -d2")',
    )

    qemu_group = parser.getgroup('embedded-qemu')
    qemu_group.addoption(
        '--qemu-image-path',
        help='QEMU image path. (Default: "<app_path>/flash_image.bin")',
    )
    qemu_group.addoption(
        '--qemu-prog-path',
        help='QEMU program path. (Default: "qemu-system-xtensa")',
    )
    qemu_group.addoption(
        '--qemu-cli-args',
        help='QEMU cli default arguments. (Default: "-nographic -no-reboot -machine esp32")',
    )
    qemu_group.addoption(
        '--qemu-extra-args',
        help='QEMU cli extra arguments, will append to the argument list. (Default: None)',
    )
    qemu_group.addoption(
        '--skip-regenerate-image',
        help='y/yes/true for True and n/no/false for False. '
        'Set to True to disable auto regenerate image. (Default: False)',
    )


###########
# helpers #
###########
_COUNT = 1
_TEST_SESSION_TMPDIR = os.path.join(
    tempfile.gettempdir(),
    'pytest-embedded',
    datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S'),
)
os.makedirs(_TEST_SESSION_TMPDIR, exist_ok=True)


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


def _str_bool(v: str) -> Union[bool, str, None]:
    if v is None:
        return None

    if v.lower() in ['y', 'yes', 'true']:
        return True
    elif v.lower() in ['n', 'no', 'false']:
        return False
    else:
        return v


def _drop_none_kwargs(kwargs: Dict[Any, Any]):
    return {k: v for k, v in kwargs.items() if v is not None}


@pytest.fixture(autouse=True)
def count(request):
    """
    Enable parametrization for the same cli option. Inject to global variable `COUNT`.
    """
    global _COUNT
    _COUNT = _gte_one_int(getattr(request, 'param', request.config.option.count))


def parse_multi_dut_args(count: int, s: str) -> Union[Any, Tuple[Any]]:
    """
    Parse multi-dut argument by the following rules:

    - When the return value is a string, split the string by `|`.
    - If the configuration value only has one item, duplicate it by the "count" amount.
    - If the configuration value item amount is the same as the "count" amount, return it directly.

    Args:
        count: Multi-Dut count
        s: argument string

    Returns:
        The argument itself. if `count` is 1.
        The tuple of the parsed argument. if `count` is greater than 1.

    Raises:
        ValueError: when a configuration has multi values but the amount is different from the `count` amount.
    """
    if isinstance(s, str):
        res = s.split('|')
    else:
        res = [s]

    if len(res) == 1:
        if count == 1:
            return _str_bool(res[0])
        else:
            return tuple([_str_bool(res[0])] * count)
    else:  # len(res) > 1
        if len(res) != count:
            raise ValueError('The configuration has multi values but the amount is different from the "count" amount.')
        else:
            return tuple(_str_bool(item) for item in res)


def multi_dut_argument(func) -> Callable[..., Union[Optional[str], Tuple[Optional[str]]]]:
    """
    Used for parse the multi-dut argument according to the `count` amount.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return parse_multi_dut_args(_COUNT, func(*args, **kwargs))

    return wrapper


def multi_dut_fixture(func) -> Callable[..., Union[Any, Tuple[Any]]]:
    """
    Apply the multi-dut arguments to each fixture.

    Notes:
        Run the `func(*args, **kwargs)` for multiple times by iterating all `kwargs` via `itemgetter`

        For example:

        - input: `{key1: (v1, v2), key2: (v1, v2)}`
        - output: `(func(**{key1: v1, key2: v1}), func(**{key1: v2, key2: v2}))`

    Returns:
        The return value, if `count` is 1.
        The tuple of return values, if `count` is greater than 1.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if _COUNT == 1:
            return func(*args, **kwargs)

        res = tuple()
        for i in range(_COUNT):
            getter = itemgetter(i)
            current_kwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, list) or isinstance(v, tuple):
                    current_kwargs[k] = getter(v)
                else:
                    current_kwargs[k] = v
            res = tuple(list(res) + [func(*args, **current_kwargs)])

        return res

    return wrapper


def multi_dut_generator_fixture(func) -> Callable[..., Generator[Union[Any, Tuple[Any]], Any, None]]:
    """
    Apply the multi-dut arguments to each fixture.

    Notes:
        Run the `func()` for multiple times by iterating all `kwargs` via `itemgetter`. Auto call `close()` or
        `terminate()` method of the object after it yield back.

    Yields:
        The return value, if `count` is 1.
        The tuple of return values, if `count` is greater than 1.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        def _close_or_terminate(obj):
            try:
                obj.close()
            except OSError:
                pass
            except AttributeError:
                try:
                    obj.terminate()
                except AttributeError:
                    pass
            finally:
                del obj

        if _COUNT == 1:
            res = None
            try:
                res = func(*args, **kwargs)
                yield res
            finally:
                if res:
                    _close_or_terminate(res)
        else:
            res = []
            for i in range(_COUNT):
                getter = itemgetter(i)
                current_kwargs = {}
                for k, v in kwargs.items():
                    if isinstance(v, list) or isinstance(v, tuple):
                        current_kwargs[k] = getter(v)
                    else:
                        current_kwargs[k] = v
                if func.__name__ in ['_pexpect_logfile', 'pexpect_proc']:
                    current_kwargs['count'] = i
                    current_kwargs['total'] = _COUNT
                res.append(func(*args, **current_kwargs))
            try:
                yield res
            finally:
                if res:
                    for item in res:
                        _close_or_terminate(item)

    return wrapper


def _request_param_or_config_option_or_default(request: FixtureRequest, option: str, default: Any = None):
    """
    Return as the following sequence:
    1. Function parametrized value
    2. CLI option value
    3. default value

    Args:
        request: fixture request
        option: cli option name
        default: default value

    Returns:
        Any
    """
    return getattr(request, 'param', None) or request.config.getoption(option, None) or default


####################
# General Fixtures #
####################
@pytest.fixture(scope='session', autouse=True)
def session_tempdir() -> str:
    """Session scoped temp dir for pytest-embedded"""
    return _TEST_SESSION_TMPDIR


@pytest.fixture
def test_file_path(request: FixtureRequest) -> str:
    """Current test script file path"""
    return request.module.__file__


@pytest.fixture
def test_case_name(request: FixtureRequest) -> str:
    """Current test case function name"""
    return request.node.name


@pytest.fixture
def test_case_tempdir(test_case_name: str, session_tempdir: str) -> str:
    """Function scoped temp dir for pytest-embedded"""
    return os.path.join(session_tempdir, test_case_name)


@pytest.fixture
@multi_dut_generator_fixture
def _pexpect_logfile(test_case_tempdir, **kwargs) -> str:
    if 'count' in kwargs:
        name = f'dut-{kwargs["count"]}'
    else:
        name = 'dut'

    return os.path.join(test_case_tempdir, f'{name}.log')


@pytest.fixture
@multi_dut_generator_fixture
def _pexpect_fw(_pexpect_logfile) -> BinaryIO:
    os.makedirs(os.path.dirname(_pexpect_logfile), exist_ok=True)
    return open(_pexpect_logfile, 'wb')


@pytest.fixture
@multi_dut_generator_fixture
def _pexpect_fr(_pexpect_logfile, _pexpect_fw) -> BinaryIO:
    return open(_pexpect_logfile, 'rb')


@pytest.fixture()
@multi_dut_argument
def with_timestamp(request: FixtureRequest) -> bool:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'with_timestamp', None)


@pytest.fixture
@multi_dut_generator_fixture
def pexpect_proc(
    _pexpect_fr, _pexpect_fw, with_timestamp, **kwargs  # kwargs passed by `multi_dut_generator_fixture()`
) -> PexpectProcess:
    """Pexpect process that run the expect functions on"""
    kwargs.update({'pexpect_fr': _pexpect_fr, 'pexpect_fw': _pexpect_fw, 'with_timestamp': with_timestamp})
    return PexpectProcess(**_drop_none_kwargs(kwargs))


@pytest.fixture
@multi_dut_generator_fixture
def redirect(pexpect_proc: PexpectProcess) -> Callable[..., DuplicateStdout]:
    """
    A context manager that could help duplicate all the `sys.stdout` to `dut.pexpect_proc`.

    ```python
    with redirect():
        print('this should be logged and sent to pexpect_proc')
    ```

    Warning:
        This is NOT thread-safe, DO NOT use this in a thread. If you want to redirect the stdout of a thread to the
        pexpect process and log it, please use `pexpect_proc.write()` instead.
    """

    def _inner():
        return DuplicateStdout(pexpect_proc)

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
    'arduino': f'{BASE_LIB_NAME}-arduino',
}

FIXTURES_SERVICES = {
    'app': ['base', 'idf', 'qemu', 'arduino'],
    'serial': ['serial', 'esp', 'idf', 'arduino'],
    'openocd': ['jtag'],
    'gdb': ['jtag'],
    'qemu': ['qemu'],
    'dut': ['base', 'serial', 'jtag', 'qemu', 'idf'],
}


###############################
# CLI Option Related Fixtures #
###############################
########
# base #
########
@pytest.fixture
@multi_dut_argument
def embedded_services(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'embedded_services', None)


@pytest.fixture
@multi_dut_argument
def app_path(request: FixtureRequest, test_file_path: str) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'app_path', os.path.dirname(test_file_path))


@pytest.fixture
@multi_dut_argument
def build_dir(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'build_dir', 'build')


##########
# serial #
##########
@pytest.fixture
@multi_dut_argument
def port(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'port', None)


#######
# esp #
#######
@pytest.fixture
@multi_dut_argument
def target(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'target', None)


@pytest.fixture
@multi_dut_argument
def baud(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'baud', None)


@pytest.fixture
@multi_dut_argument
def skip_autoflash(request: FixtureRequest) -> Optional[bool]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'skip_autoflash', None)


#######
# idf #
#######
@pytest.fixture
@multi_dut_argument
def part_tool(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'part_tool', None)


@pytest.fixture
@multi_dut_argument
def confirm_target_elf_sha256(request: FixtureRequest) -> Optional[bool]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'confirm_target_elf_sha256', None)


@pytest.fixture
@multi_dut_argument
def erase_nvs(request: FixtureRequest) -> Optional[bool]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'erase_nvs', None)


@pytest.fixture
@multi_dut_argument
def skip_check_coredump(request: FixtureRequest) -> Optional[bool]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'skip_check_coredump', None)


########
# jtag #
########
@pytest.fixture
@multi_dut_argument
def gdb_prog_path(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'gdb_prog_path', None)


@pytest.fixture
@multi_dut_argument
def gdb_cli_args(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'gdb_cli_args', None)


@pytest.fixture
@multi_dut_argument
def openocd_prog_path(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'openocd_prog_path', None)


@pytest.fixture
@multi_dut_argument
def openocd_cli_args(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'openocd_cli_args', None)


########
# qemu #
########
@pytest.fixture
@multi_dut_argument
def qemu_image_path(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'qemu_image_path', None)


@pytest.fixture
@multi_dut_argument
def qemu_prog_path(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'qemu_prog_path', None)


@pytest.fixture
@multi_dut_argument
def qemu_cli_args(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'qemu_cli_args', None)


@pytest.fixture
@multi_dut_argument
def qemu_extra_args(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'qemu_extra_args', None)


@pytest.fixture
@multi_dut_argument
def skip_regenerate_image(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'skip_regenerate_image', None)


####################
# Private Fixtures #
####################
@pytest.fixture
@multi_dut_fixture
def _services(embedded_services: Optional[str]) -> List[str]:
    if not embedded_services:
        return ['base']

    services = [s for s in embedded_services.split(',') if s]

    for s in services:
        if s not in SERVICE_LIB_NAMES.keys():
            raise ValueError(f'service "{s}" not available, please run "--help" for more information')

        try:
            importlib.import_module(SERVICE_LIB_NAMES[s].replace('-', '_'))
        except ModuleNotFoundError:
            logging.error(f'Please install {SERVICE_LIB_NAMES[s]} to enable service {s}')
            sys.exit(1)

    return ['base'] + services


ClassCliOptions = namedtuple('ClassCliOptions', ['classes', 'kwargs'])  # Tuple[Dict[str, type], Dict[str, list[str]]]


@pytest.fixture
@multi_dut_fixture
def _fixture_classes_and_options(
    _services,
    # parametrize fixtures
    app_path,
    build_dir,
    port,
    target,
    baud,
    skip_autoflash,
    part_tool,
    confirm_target_elf_sha256,
    erase_nvs,
    skip_check_coredump,
    openocd_prog_path,
    openocd_cli_args,
    gdb_prog_path,
    gdb_cli_args,
    qemu_image_path,
    qemu_prog_path,
    qemu_cli_args,
    qemu_extra_args,
    skip_regenerate_image,
    # pre-initialized fixtures
    _pexpect_logfile,
    test_case_name,
    pexpect_proc,
) -> ClassCliOptions:
    """
    classes: the class that the fixture should instantiate
    {
        <fixture_name>: <class_name>,
        ...
    }

    kwargs: the `**kwargs` dict used for initializing the class
    {
        <fixture_name>: {
            <kwargs-key>: <value>,
            ...
        },
        }
    }
        ...
    }
    """
    classes: Dict[str, type] = {}
    kwargs: Dict[str, Dict[str, Any]] = defaultdict(dict)

    for fixture, provide_services in FIXTURES_SERVICES.items():
        if fixture == 'app':
            kwargs['app'] = {'app_path': app_path, 'build_dir': build_dir}
            if 'idf' in _services:
                if 'qemu' in _services:
                    from pytest_embedded_qemu.app import DEFAULT_IMAGE_FN, QemuApp

                    classes[fixture] = QemuApp
                    kwargs[fixture].update(
                        {
                            'pexpect_proc': pexpect_proc,
                            'part_tool': part_tool,
                            'qemu_image_path': qemu_image_path,
                            'skip_regenerate_image': skip_regenerate_image,
                        }
                    )
                else:
                    from pytest_embedded_idf.app import IdfApp

                    classes[fixture] = IdfApp
                    kwargs[fixture].update(
                        {
                            'pexpect_proc': pexpect_proc,
                            'part_tool': part_tool,
                        }
                    )
            elif 'arduino' in _services:
                from pytest_embedded_arduino.app import ArduinoApp

                classes[fixture] = ArduinoApp
                kwargs[fixture].update(
                    {
                        'pexpect_proc': pexpect_proc,
                    }
                )
            else:
                from .app import App

                classes[fixture] = App
        elif fixture == 'serial':
            if 'esp' in _services:
                from pytest_embedded_serial_esp.serial import EspSerial

                kwargs[fixture] = {
                    'pexpect_proc': pexpect_proc,
                    'target': target,
                    'port': os.getenv('ESPPORT') or port,
                    'baud': int(os.getenv('ESPBAUD') or baud or EspSerial.DEFAULT_BAUDRATE),
                    'skip_autoflash': skip_autoflash,
                }
                if 'idf' in _services:
                    from pytest_embedded_idf.serial import IdfSerial

                    classes[fixture] = IdfSerial
                    kwargs[fixture].update(
                        {
                            'app': None,
                            'confirm_target_elf_sha256': confirm_target_elf_sha256,
                            'erase_nvs': erase_nvs,
                        }
                    )
                elif 'arduino' in _services:
                    from pytest_embedded_arduino.serial import ArduinoSerial

                    classes[fixture] = ArduinoSerial
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
                    'pexpect_proc': pexpect_proc,
                    'port': port,
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
                from pytest_embedded_qemu.app import DEFAULT_IMAGE_FN
                from pytest_embedded_qemu.qemu import Qemu

                classes[fixture] = Qemu
                kwargs[fixture] = {
                    'qemu_image_path': qemu_image_path
                    or os.path.join(app_path or '', build_dir or 'build', DEFAULT_IMAGE_FN),
                    'qemu_prog_path': qemu_prog_path,
                    'qemu_cli_args': qemu_cli_args,
                    'qemu_extra_args': qemu_extra_args,
                }
        elif fixture == 'dut':
            kwargs[fixture] = {
                'pexpect_proc': pexpect_proc,
                'app': None,
                'pexpect_logfile': _pexpect_logfile,
                'test_case_name': test_case_name,
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
                if 'esp' in _services and 'idf' in _services:
                    from pytest_embedded_idf.dut import IdfDut

                    classes[fixture] = IdfDut
                    kwargs[fixture].update(
                        {
                            'skip_check_coredump': skip_check_coredump,
                        }
                    )
                else:
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
@multi_dut_fixture
def app(_fixture_classes_and_options: ClassCliOptions) -> App:
    """A pytest fixture to gather information from the specified built binary folder"""
    cls = _fixture_classes_and_options.classes['app']
    kwargs = _fixture_classes_and_options.kwargs['app']
    return cls(**_drop_none_kwargs(kwargs))


@pytest.fixture
@multi_dut_generator_fixture
def serial(_fixture_classes_and_options, app) -> Optional['Serial']:
    """A serial subprocess that could read/redirect/write"""
    if 'serial' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['serial']
    kwargs = _fixture_classes_and_options.kwargs['serial']
    if 'app' in kwargs and kwargs['app'] is None:
        kwargs['app'] = app
    return cls(**_drop_none_kwargs(kwargs))


@pytest.fixture
@multi_dut_generator_fixture
def openocd(_fixture_classes_and_options: ClassCliOptions) -> Optional['OpenOcd']:
    """An openocd subprocess that could read/redirect/write"""
    if 'openocd' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['openocd']
    kwargs = _fixture_classes_and_options.kwargs['openocd']
    return cls(**_drop_none_kwargs(kwargs))


@pytest.fixture
@multi_dut_generator_fixture
def gdb(_fixture_classes_and_options: ClassCliOptions) -> Optional['Gdb']:
    """A gdb subprocess that could read/redirect/write"""
    if 'gdb' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['gdb']
    kwargs = _fixture_classes_and_options.kwargs['gdb']
    return cls(**_drop_none_kwargs(kwargs))


@pytest.fixture
@multi_dut_generator_fixture
def qemu(_fixture_classes_and_options: ClassCliOptions) -> Optional['Qemu']:
    """A qemu subprocess that could read/redirect/write"""
    if 'qemu' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['qemu']
    kwargs = _fixture_classes_and_options.kwargs['qemu']
    return cls(**_drop_none_kwargs(kwargs))


@pytest.fixture
@multi_dut_generator_fixture
def dut(
    _fixture_classes_and_options: ClassCliOptions,
    app: App,
    serial: Optional['Serial'],
    openocd: Optional['OpenOcd'],
    gdb: Optional['Gdb'],
    qemu: Optional['Qemu'],
) -> Dut:
    """
    A device under test (DUT) object that could gather output from various sources and redirect them to the pexpect
    process, and run `expect()` via its pexpect process.
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
    return cls(**_drop_none_kwargs(kwargs))


##################
# Hook Functions #
##################
_junit_merger_key = pytest.StashKey['JunitMerger']()
_pytest_embedded_key = pytest.StashKey['PytestEmbedded']()
_port_target_cache_key = pytest.StashKey[str]()
_port_app_cache_key = pytest.StashKey[str]()


def pytest_configure(config: Config) -> None:
    port_target_cache: Dict[str, str] = {}
    port_app_cache: Dict[str, str] = {}

    config.stash[_junit_merger_key] = JunitMerger(config.option.xmlpath)
    config.stash[_port_target_cache_key] = port_target_cache
    config.stash[_port_app_cache_key] = port_app_cache

    config.stash[_pytest_embedded_key] = PytestEmbedded(
        parallel_count=config.getoption('parallel_count'),
        parallel_index=config.getoption('parallel_index'),
        port_target_cache=port_target_cache,
        port_app_cache=port_app_cache,
    )
    config.pluginmanager.register(config.stash[_pytest_embedded_key])


def pytest_unconfigure(config: Config) -> None:
    _pytest_embedded = config.stash.get(_pytest_embedded_key, None)
    if _pytest_embedded:
        del config.stash[_pytest_embedded_key]
        config.pluginmanager.unregister(_pytest_embedded)


class PytestEmbedded:
    def __init__(
        self,
        parallel_count: int = 1,
        parallel_index: int = 1,
        port_target_cache: Dict[str, str] = None,
        port_app_cache: Dict[str, str] = None,
    ):
        self.parallel_count = parallel_count
        self.parallel_index = parallel_index

        self._port_target_cache = port_target_cache
        self._port_app_cache = port_app_cache

    @staticmethod
    def _raise_dut_failed_cases_if_exists(duts: Iterable[Dut]) -> None:
        failed_cases = []
        for _dut in duts:
            if _dut.testsuite.failed_cases:
                failed_cases.extend(_dut.testsuite.failed_cases)

        if failed_cases:
            logging.error('Failed Cases:')
            for case in failed_cases:
                logging.error(f'  - {case.name}')
            raise AssertionError('Unity test failed')

    @staticmethod
    def _pytest_fixturedef_get_kwargs(fixturedef: FixtureDef[Any], request: SubRequest) -> Dict[str, Any]:
        kwargs = {}
        for argname in fixturedef.argnames:
            fixdef = request._get_active_fixturedef(argname)
            assert fixdef.cached_result is not None
            result, arg_cache_key, exc = fixdef.cached_result
            request._check_scope(argname, request._scope, fixdef._scope)
            kwargs[argname] = result

        return kwargs

    @staticmethod
    def _pytest_fixturedef_exec(fixturedef: FixtureDef[Any], request: SubRequest, kwargs: Dict[str, Any]):
        fixturefunc = resolve_fixture_function(fixturedef, request)
        my_cache_key = fixturedef.cache_key(request)
        try:
            result = call_fixture_func(fixturefunc, request, kwargs)
        except TEST_OUTCOME:
            exc_info = sys.exc_info()
            assert exc_info[0] is not None
            fixturedef.cached_result = (None, my_cache_key, exc_info)
            raise
        fixturedef.cached_result = (result, my_cache_key, None)
        return result

    @pytest.hookimpl(tryfirst=True)
    def pytest_fixture_setup(self, fixturedef: FixtureDef[Any], request: SubRequest):
        if fixturedef.argname != 'serial':
            return

        # inject the cache into the serial kwargs
        kwargs = self._pytest_fixturedef_get_kwargs(fixturedef, request)
        _class_cli_options = kwargs['_fixture_classes_and_options']

        # compatible to multi-dut
        if isinstance(_class_cli_options, ClassCliOptions):
            iterable_class_cli_options = [_class_cli_options]
        else:
            iterable_class_cli_options = _class_cli_options

        for _item in iterable_class_cli_options:
            _item_cls = _item.classes.get('serial')
            _item_kwargs = _item.kwargs.get('serial')

            if _item_cls is None or _item_kwargs is None:
                continue

            if _item_cls.__name__ == 'IdfSerial':  # use str to avoid ImportError
                _item_kwargs['port_target_cache'] = self._port_target_cache
                _item_kwargs['port_app_cache'] = self._port_app_cache
            elif _item_cls.__name__ == 'EspSerial':  # use str to avoid ImportError
                _item_kwargs['port_target_cache'] = self._port_target_cache

        return self._pytest_fixturedef_exec(fixturedef, request, kwargs)

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items: List[Function]):
        if self.parallel_index == 1 and self.parallel_count == 1:
            return

        current_job_index = self.parallel_index - 1  # convert to 0-based index
        max_cases_num_per_job = (len(items) + self.parallel_count - 1) // self.parallel_count

        run_case_start_index = max_cases_num_per_job * current_job_index
        if run_case_start_index >= len(items):
            logging.warning(
                f'Nothing to do for job {current_job_index + 1} '
                f'(case total: {len(items)}, per job: {max_cases_num_per_job})'
            )
            items.clear()
            return

        run_case_end_index = min(max_cases_num_per_job * (current_job_index + 1) - 1, len(items) - 1)
        logging.info(
            f'Total {len(items)} cases, max {max_cases_num_per_job} cases per job, '
            f'running test cases {run_case_start_index + 1}-{run_case_end_index + 1}'
        )
        items[:] = items[run_case_start_index : run_case_end_index + 1]

    @pytest.hookimpl(trylast=True)
    def pytest_runtest_call(self, item: Function):
        # raise dut failed cases
        if 'dut' in item.funcargs:
            duts = to_list(item.funcargs['dut'])
            self._raise_dut_failed_cases_if_exists(duts)  # type: ignore

    @pytest.hookimpl(trylast=True)  # combine all possible junit reports should be the last step
    def pytest_sessionfinish(self, session: Session, exitstatus: int) -> None:  # noqa
        modifier: JunitMerger = session.config.stash[_junit_merger_key]
        modifier.merge(find_by_suffix('.xml', _TEST_SESSION_TMPDIR))
        exitstatus = int(modifier.failed)  # True -> 1  False -> 0  # noqa
