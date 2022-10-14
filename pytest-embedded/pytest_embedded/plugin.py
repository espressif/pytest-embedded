import contextlib
import datetime
import functools
import importlib
import io
import logging
import multiprocessing
import os
import subprocess
import sys
import tempfile
from collections import defaultdict, namedtuple
from operator import itemgetter
from pathlib import Path
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
from .log import MessageQueue, PexpectProcess
from .unity import JunitMerger
from .utils import Meta, find_by_suffix, to_list, to_str

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
        '--parallel-count',
        default=1,
        type=_gte_one_int,
        help='Number of parallel build jobs. (Default: 1)',
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
    base_group.addoption('--root-logdir', help='set session-based root log dir. (Default: system temp folder)')

    serial_group = parser.getgroup('embedded-serial')
    serial_group.addoption('--port', help='serial port. (Env: "ESPPORT" if service "esp" specified, Default: "None")')
    serial_group.addoption(
        '--port-location', help='USB device location string ("<bus>-<port>[-<port>]…"). Default: None'
    )
    serial_group.addoption(
        '--baud',
        help='serial port communication baud rate. (Default: 115200)',
    )

    esp_group = parser.getgroup('embedded-esp')
    esp_group.addoption('--target', help='serial target chip type. (Default: "auto")')
    esp_group.addoption('--beta-target', help='serial target beta version chip type. (Default: same as [--target])')
    esp_group.addoption(
        '--skip-autoflash',
        help='y/yes/true for True and n/no/false for False. Set to True to disable auto flash. (Default: False)',
    )
    esp_group.addoption(
        '--erase-all',
        help='y/yes/true for True and n/no/false for False. Set to True to erase all flash before programming. '
        '(Default: False)',
    )
    esp_group.addoption(
        '--esptool-baud',
        help='esptool flashing baud rate. (Env: "ESPBAUD" if service "esp" specified, Default: 921600)',
    )
    esp_group.addoption(
        '--port-mac',
        help='MAC address of the board. (Default: None)',
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
        'Set to True to skip auto check core dump in UART/flash '
        'and panic handler support while teardown the failing test case. '
        'Requires valid partition tool, project_description.json under the build dir. (Default: False)',
    )
    idf_group.addoption(
        '--panic-output-decode-script',
        help='Panic output decode script that is used in conjunction with the check-panic-coredump option '
        'to parse panic output. (Default: $IDF_PATH/tools/gdb_panic_server.py)',
    )

    jtag_group = parser.getgroup('embedded-jtag')
    jtag_group.addoption('--gdb-prog-path', help='GDB program path. (Default: "xtensa-esp32-elf-gdb")')
    jtag_group.addoption(
        '--gdb-cli-args',
        help='GDB cli arguments. (Default: "--quiet"',
    )
    jtag_group.addoption('--openocd-prog-path', help='openocd program path. (Default: "openocd")')
    jtag_group.addoption(
        '--openocd-cli-args',
        help='openocd cli arguments. (Default: "-f board/esp32-wrover-kit-3.3v.cfg")',
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

    if isinstance(v, str) and v.lower() in ['y', 'yes', 'true']:
        return True
    elif isinstance(v, str) and v.lower() in ['n', 'no', 'false']:
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
            if func.__name__ == 'dut_index':
                kwargs['count'] = 1
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

            if func.__name__ == 'dut_index':
                current_kwargs['count'] = i

            res = tuple(list(res) + [func(*args, **current_kwargs)])

        return res

    return wrapper


def multi_dut_generator_fixture(
    func,
) -> Callable[..., Generator[Union[Any, Tuple[Any]], Any, None]]:
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
                if isinstance(obj, subprocess.Popen):
                    obj.terminate()
                    obj.kill()
                elif isinstance(obj, multiprocessing.Process):
                    obj.terminate()
                    obj.kill()
                elif isinstance(obj, io.IOBase):
                    try:
                        obj.close()
                    except Exception as e:
                        logging.debug('file close failed')
                        logging.debug(str(e))
                        raise
            except Exception as e:
                logging.debug('%s: %s', obj, str(e))
                return  # swallow up all error

            try:
                obj.close()
            except AttributeError:
                try:
                    obj.terminate()
                except AttributeError:
                    pass
            except Exception as e:
                logging.debug('Not properly caught object %s: %s', obj, str(e))
                return  # swallow up all error

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


###################
# Helper Fixtures #
###################
@pytest.fixture
def test_file_path(request: FixtureRequest) -> str:
    """Current test script file path"""
    return request.module.__file__


@pytest.fixture
def test_case_name(request: FixtureRequest) -> str:
    """Current test case function name"""
    return request.node.name


###########################
# Pre-initialize Fixtures #
###########################
@pytest.fixture(scope='session')
def session_root_logdir(request: FixtureRequest) -> str:
    """Session scoped log dir for pytest-embedded"""
    return os.path.realpath(_request_param_or_config_option_or_default(request, 'root_logdir', tempfile.gettempdir()))


@pytest.fixture(scope='session')
def session_tempdir(session_root_logdir) -> str:
    """Session scoped temp dir for pytest-embedded"""
    _tmpdir = os.path.join(
        session_root_logdir,
        'pytest-embedded',
        f'{datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S-%f")}',
    )
    os.makedirs(_tmpdir, exist_ok=True)
    return _tmpdir


@pytest.fixture(scope='session')
def port_target_cache() -> Dict[str, str]:
    """Session scoped port-target cache, for esp only"""
    return {}


@pytest.fixture(scope='session')
def port_app_cache() -> Dict[str, str]:
    """Session scoped port-app cache, for idf only"""
    return {}


@pytest.fixture(scope='session')
def _meta(session_tempdir, port_target_cache, port_app_cache) -> Meta:
    """Session scoped _meta info"""
    return Meta(session_tempdir, port_target_cache, port_app_cache)


@pytest.fixture
def test_case_tempdir(test_case_name: str, session_tempdir: str) -> str:
    """Function scoped temp dir for pytest-embedded"""
    return os.path.join(session_tempdir, test_case_name)


@pytest.fixture
@multi_dut_fixture
def dut_index(**kwargs):
    return kwargs['count']


@pytest.fixture
@multi_dut_fixture
def dut_total():
    return _COUNT


@pytest.fixture
@multi_dut_fixture
def _pexpect_logfile(test_case_tempdir, dut_index, dut_total) -> str:
    if dut_total > 1:
        name = f'dut-{dut_index}'
    else:
        name = 'dut'

    return os.path.join(test_case_tempdir, f'{name}.log')


# Suppress UserWarning on resource_tracker.py
if sys.platform == 'darwin':
    multiprocessing.set_start_method('fork')

_ctx = multiprocessing.get_context()
_stdout = sys.__stdout__


@pytest.fixture
@multi_dut_generator_fixture
def msg_queue() -> MessageQueue:  # kwargs passed by `multi_dut_generator_fixture()`
    return MessageQueue(ctx=_ctx)


@pytest.fixture()
@multi_dut_argument
def with_timestamp(request: FixtureRequest) -> bool:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'with_timestamp', None)


def _listen(q: MessageQueue, filepath: str, with_timestamp: bool = True, count: int = 1, total: int = 1) -> None:
    _added_prefix = False
    while True:
        msg = q.get()
        if not msg:
            continue

        with open(filepath, 'ab') as fw:
            fw.write(msg)
            fw.flush()

        _s = to_str(msg)
        if not _s:
            continue

        prefix = ''
        if total > 1:
            source = f'dut-{count}'
        else:
            source = None

        if source:
            prefix = f'[{source}] ' + prefix

        if with_timestamp:
            prefix = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + prefix

        if not _added_prefix:
            _s = prefix + _s
            _added_prefix = True
        _s = _s.replace('\n', '\n' + prefix)
        if prefix and _s.endswith(prefix):
            _s = _s.rsplit(prefix, maxsplit=1)[0]
            _added_prefix = False

        _stdout.write(_s)
        _stdout.flush()


@pytest.fixture
# here we use @multi_dut_fixture
# The daemon process should be closed at the very last. would be auto closed.
@multi_dut_fixture
def _listener(msg_queue, _pexpect_logfile, with_timestamp, dut_index, dut_total) -> multiprocessing.Process:
    """
    The listener would create a `_listen` process. The `_listen` process would get the string from the message queue,
    and do two things together:

    1. print the string to `sys.stdout`
    2. write the string to `_pexpect_logfile`
    """
    os.makedirs(os.path.dirname(_pexpect_logfile), exist_ok=True)
    kwargs = {
        'with_timestamp': with_timestamp,
        'count': dut_index,
        'total': dut_total,
    }

    return _ctx.Process(
        target=_listen,
        args=(
            msg_queue,
            _pexpect_logfile,
        ),
        kwargs=_drop_none_kwargs(kwargs),
        daemon=True,
    )


@pytest.fixture
@multi_dut_generator_fixture
def _pexpect_fr(_pexpect_logfile, _listener) -> BinaryIO:
    Path(_pexpect_logfile).touch()
    _listener.start()
    return open(_pexpect_logfile, 'rb')


@pytest.fixture
# here we use @multi_dut_fixture
# otherwise the close() method would be called, and would raise the OSError
# The file descriptor would be closed at `_pexpect_fr`
@multi_dut_fixture
def pexpect_proc(_pexpect_fr) -> PexpectProcess:
    """Pexpect process that run the expect functions on"""
    return PexpectProcess(_pexpect_fr)


@pytest.fixture
@multi_dut_generator_fixture
def redirect(msg_queue: MessageQueue) -> Callable[..., contextlib.redirect_stdout]:
    """
    A context manager that could help duplicate all the `sys.stdout` to `msg_queue`.
    ```python
    with redirect():
        print('this should be logged and sent to pexpect_proc')
    ```
    """

    def _inner():
        return contextlib.redirect_stdout(msg_queue)

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
    'serial': ['serial', 'jtag', 'esp', 'idf', 'arduino'],
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


@pytest.fixture
@multi_dut_argument
def baud(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'baud', None)


@pytest.fixture
@multi_dut_argument
def port_location(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'port_location', None)


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
def beta_target(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'beta_target', None)


@pytest.fixture
@multi_dut_argument
def skip_autoflash(request: FixtureRequest) -> Optional[bool]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'skip_autoflash', None)


@pytest.fixture
@multi_dut_argument
def erase_all(request: FixtureRequest) -> Optional[bool]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'erase_all', None)


@pytest.fixture
@multi_dut_argument
def esptool_baud(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'esptool_baud', None)


@pytest.fixture
@multi_dut_argument
def port_mac(request: FixtureRequest) -> Optional[str]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'port_mac', None)


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


@pytest.fixture
@multi_dut_argument
def panic_output_decode_script(request: FixtureRequest) -> Optional[bool]:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'panic_output_decode_script', None)


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
    port_location,
    port_mac,
    target,
    beta_target,
    baud,
    skip_autoflash,
    erase_all,
    esptool_baud,
    part_tool,
    confirm_target_elf_sha256,
    erase_nvs,
    skip_check_coredump,
    panic_output_decode_script,
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
    dut_index,
    _pexpect_logfile,
    test_case_name,
    pexpect_proc,
    msg_queue,
    _meta,
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

    for fixture, _ in FIXTURES_SERVICES.items():
        if fixture == 'app':
            kwargs['app'] = {'app_path': app_path, 'build_dir': build_dir}
            if 'idf' in _services:
                if 'qemu' in _services:
                    from pytest_embedded_qemu import DEFAULT_IMAGE_FN, QemuApp

                    classes[fixture] = QemuApp
                    kwargs[fixture].update(
                        {
                            'msg_queue': msg_queue,
                            'part_tool': part_tool,
                            'qemu_image_path': qemu_image_path,
                            'skip_regenerate_image': skip_regenerate_image,
                        }
                    )
                else:
                    from pytest_embedded_idf import IdfApp

                    classes[fixture] = IdfApp
                    kwargs[fixture].update(
                        {
                            'part_tool': part_tool,
                        }
                    )
            elif 'arduino' in _services:
                from pytest_embedded_arduino import ArduinoApp

                classes[fixture] = ArduinoApp
            else:
                from .app import App

                classes[fixture] = App
        elif fixture == 'serial':
            if 'esp' in _services:
                from pytest_embedded_serial_esp import EspSerial

                kwargs[fixture] = {
                    'pexpect_proc': pexpect_proc,
                    'msg_queue': msg_queue,
                    'target': target,
                    'beta_target': beta_target,
                    'port': os.getenv('ESPPORT') or port,
                    'port_location': port_location,
                    'port_mac': port_mac,
                    'baud': int(baud or EspSerial.DEFAULT_BAUDRATE),
                    'esptool_baud': int(os.getenv('ESPBAUD') or esptool_baud or EspSerial.ESPTOOL_DEFAULT_BAUDRATE),
                    'skip_autoflash': skip_autoflash,
                    'erase_all': erase_all,
                    'meta': _meta,
                }
                if 'idf' in _services:
                    from pytest_embedded_idf import IdfSerial

                    classes[fixture] = IdfSerial
                    kwargs[fixture].update(
                        {
                            'app': None,
                            'confirm_target_elf_sha256': confirm_target_elf_sha256,
                            'erase_nvs': erase_nvs,
                        }
                    )
                elif 'arduino' in _services:
                    from pytest_embedded_arduino import ArduinoSerial

                    classes[fixture] = ArduinoSerial
                    kwargs[fixture].update(
                        {
                            'app': None,
                        }
                    )
                else:
                    from pytest_embedded_serial_esp import EspSerial

                    classes[fixture] = EspSerial
            elif 'serial' in _services or 'jtag' in _services:
                from pytest_embedded_serial.serial import Serial

                classes[fixture] = Serial
                kwargs[fixture] = {
                    'msg_queue': msg_queue,
                    'port': port,
                    'port_location': port_location,
                    'baud': int(baud or Serial.DEFAULT_BAUDRATE),
                    'meta': _meta,
                }
        elif fixture in ['openocd', 'gdb']:
            if 'jtag' in _services:
                if fixture == 'openocd':
                    from pytest_embedded_jtag import OpenOcd

                    classes[fixture] = OpenOcd
                    kwargs[fixture] = {
                        'msg_queue': msg_queue,
                        'app': None,
                        'openocd_prog_path': openocd_prog_path,
                        'openocd_cli_args': openocd_cli_args,
                        'port_offset': dut_index,
                        'meta': _meta,
                    }
                else:
                    from pytest_embedded_jtag import Gdb

                    classes[fixture] = Gdb
                    kwargs[fixture] = {
                        'msg_queue': msg_queue,
                        'gdb_prog_path': gdb_prog_path,
                        'gdb_cli_args': gdb_cli_args,
                        'meta': _meta,
                    }
        elif fixture == 'qemu':
            if 'qemu' in _services:
                from pytest_embedded_qemu import DEFAULT_IMAGE_FN, Qemu

                classes[fixture] = Qemu
                kwargs[fixture] = {
                    'msg_queue': msg_queue,
                    'qemu_image_path': qemu_image_path
                    or os.path.join(app_path or '', build_dir or 'build', DEFAULT_IMAGE_FN),
                    'qemu_prog_path': qemu_prog_path,
                    'qemu_cli_args': qemu_cli_args,
                    'qemu_extra_args': qemu_extra_args,
                    'meta': _meta,
                }
        elif fixture == 'dut':
            classes[fixture] = Dut
            kwargs[fixture] = {
                'pexpect_proc': pexpect_proc,
                'msg_queue': msg_queue,
                'app': None,
                'pexpect_logfile': _pexpect_logfile,
                'test_case_name': test_case_name,
                'meta': _meta,
            }
            if 'qemu' in _services:
                from pytest_embedded_qemu import QemuDut

                classes[fixture] = QemuDut
                kwargs[fixture].update(
                    {
                        'qemu': None,
                    }
                )
            elif 'jtag' in _services:
                if 'idf' in _services:
                    from pytest_embedded_idf import IdfDut

                    classes[fixture] = IdfDut
                else:
                    from pytest_embedded_serial import SerialDut

                    classes[fixture] = SerialDut

                kwargs[fixture].update(
                    {
                        'serial': None,
                        'openocd': None,
                        'gdb': None,
                    }
                )
            elif 'serial' in _services or 'esp' in _services:
                if 'esp' in _services and 'idf' in _services:
                    from pytest_embedded_idf import IdfDut

                    classes[fixture] = IdfDut
                    kwargs[fixture].update(
                        {
                            'skip_check_coredump': skip_check_coredump,
                            'panic_output_decode_script': panic_output_decode_script,
                        }
                    )
                else:
                    from pytest_embedded_serial import SerialDut

                    classes[fixture] = SerialDut

                kwargs[fixture].update(
                    {
                        'serial': None,
                    }
                )

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
_session_tempdir_key = pytest.StashKey['session_tempdir']()


def pytest_configure(config: Config) -> None:
    config.stash[_junit_merger_key] = JunitMerger(config.option.xmlpath)

    config.stash[_pytest_embedded_key] = PytestEmbedded(
        parallel_count=config.getoption('parallel_count'),
        parallel_index=config.getoption('parallel_index'),
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
    ):
        self.parallel_count = parallel_count
        self.parallel_index = parallel_index

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
        # record session_tempdir in session stash
        if fixturedef.argname == 'session_tempdir':
            kwargs = self._pytest_fixturedef_get_kwargs(fixturedef, request)
            val = self._pytest_fixturedef_exec(fixturedef, request, kwargs)
            request.config.stash[_session_tempdir_key] = val
            return val

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
            duts = [dut for dut in to_list(item.funcargs['dut']) if isinstance(dut, Dut)]
            self._raise_dut_failed_cases_if_exists(duts)  # type: ignore

    @pytest.hookimpl(trylast=True)  # combine all possible junit reports should be the last step
    def pytest_sessionfinish(self, session: Session, exitstatus: int) -> None:  # noqa
        modifier: JunitMerger = session.config.stash[_junit_merger_key]
        _stash_session_tempdir = session.config.stash.get(_session_tempdir_key, None)
        if _stash_session_tempdir is not None:
            modifier.merge(find_by_suffix('.xml', _stash_session_tempdir))
        exitstatus = int(modifier.failed)  # True -> 1  False -> 0  # noqa
