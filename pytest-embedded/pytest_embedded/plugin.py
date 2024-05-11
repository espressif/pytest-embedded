import argparse
import contextlib
import dbm
import functools
import gc
import importlib
import io
import logging
import multiprocessing
import os
import shelve
import subprocess
import tempfile
import typing as t
import warnings
import xml.dom.minidom
from collections import Counter
from operator import itemgetter

import filelock
import pytest
from _pytest.config import Config
from _pytest.fixtures import (
    FixtureRequest,
)
from _pytest.main import Session
from _pytest.python import Function

from .app import App
from .dut import Dut
from .dut_factory import (
    DutFactory,
    _fixture_classes_and_options_fn,
    _listener_gn,
    _pexpect_fr_gn,
    app_fn,
    dut_gn,
    gdb_gn,
    openocd_gn,
    pexpect_proc_fn,
    qemu_gn,
    serial_gn,
    set_parametrized_fixtures_cache,
    wokwi_gn,
)
from .log import MessageQueue, MessageQueueManager, PexpectProcess
from .unity import JunitMerger, UnityTestReportMode, escape_illegal_xml_chars
from .utils import (
    SERVICE_LIB_NAMES,
    ClassCliOptions,
    Meta,
    PackageNotInstalledError,
    UnknownServiceError,
    find_by_suffix,
    targets_to_marker,
    to_list,
    utcnow_str,
)

if t.TYPE_CHECKING:
    from pytest_embedded_idf import CaseTester, IdfDut, LinuxSerial
    from pytest_embedded_jtag import Gdb, OpenOcd
    from pytest_embedded_qemu import Qemu
    from pytest_embedded_serial import Serial
    from pytest_embedded_wokwi import Wokwi


_T = t.TypeVar('_T')


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
        '--check-duplicates',
        help='y/yes/true for True and n/no/false for False. '
        'Set to True to check if there were test cases or test scripts with the same name. (Default: False)',
    )
    base_group.addoption(
        '--prettify-junit-report',
        help='y/yes/true for True and n/no/false for False. Set to True to prettify XML junit report. (Default: False)',
    )
    parser.addoption(
        '--unity-test-report-mode',
        choices=[mode.value for mode in UnityTestReportMode],
        default=UnityTestReportMode.REPLACE.value,
        help=(
            'Specify the behavior for handling Unity test cases in the main JUnit report. '
            "'merge' includes them alongside the parent Python test case. "
            "'replace' substitutes the parent Python test case with Unity test cases (default)."
        ),
    )

    # supports parametrization
    base_group.addoption('--root-logdir', help='set session-based root log dir. (Default: system temp folder)')
    base_group.addoption(
        '--cache-dir', help='set root cache-dir for storing cache files. \n(Default: system temp folder)'
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
        '- wokwi: use wokwi simulator instead of the real target\n'
        '- nuttx: service for nuttx project, optionally with espressif devices\n'
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
        '--logfile-extension', default='.log', help='set the extension format of the log files. (Default: ".log")'
    )

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
        '--add-target-as-marker-with-amount',
        help='add target param as a function marker with the amount of the target. Useful in CI with runners with '
        'different tags. y/yes/true for True and n/no/false for False. '
        '(Default: False, parametrization not supported, `|` will be escaped to `+`)',
    )
    esp_group.addoption(
        '--flash-port',
        help='serial port for flashing. Only set this value when the flashing port is different from the serial port.'
        '(Default: None)',
    )
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
    esp_group.addoption(
        '--port-serial-number', help='Comma-separated list of serial numbers to filter ports by. (Default: None)'
    )
    esp_group.addoption(
        '--esp-flash-force',
        action='store_true',
        help='force mode for esptool',
    )
    idf_group = parser.getgroup('embedded-idf')
    idf_group.addoption(
        '--supported-targets', help='Comma-separated list of supported targets for the test case. (Default: None)'
    )
    idf_group.addoption(
        '--preview-targets', help='Comma-separated list of preview targets for the test case. (Default: None)'
    )
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
    jtag_group.addoption(
        '--no-gdb',
        help='y/yes/true for True and n/no/false for False. '
        'Set to True to skip create gdb instance automatically. (Default: False)',
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
        help='QEMU cli default arguments. (Default: "-nographic -machine esp32")',
    )
    qemu_group.addoption(
        '--qemu-extra-args',
        help='QEMU cli extra arguments, will append to the argument list. (Default: None)',
    )
    qemu_group.addoption(
        '--qemu-efuse-path',
        help='This option makes it possible to use efuse in QEMU when it is set up.',
    )
    qemu_group.addoption(
        '--skip-regenerate-image',
        help='y/yes/true for True and n/no/false for False. '
        'Set to True to disable auto regenerate image. (Default: False)',
    )
    qemu_group.addoption(
        '--encrypt',
        help='y/yes/true for True and n/no/false for False. Set to True for pre-encryption workflow (Default: False)',
    )
    qemu_group.addoption(
        '--keyfile',
        help='Flash Encryption (pre-encrypted workflow) key path. (Default: None)',
    )

    wokwi_group = parser.getgroup('embedded-wokwi')
    wokwi_group.addoption(
        '--wokwi-diagram',
        help='Path to the wokwi diagram file (Default: None)',
    )


###########
# helpers #
###########
_COUNT = 1
_MP_MANAGER: MessageQueueManager | None = None


def _gte_one_int(v) -> int:
    try:
        v = int(v)
    except Exception:
        pass  # deal with it later
    else:
        if v >= 1:
            return v

    raise argparse.ArgumentTypeError('should be a integer greater or equal to 1')


def _str_bool(v: str) -> bool | str | None:
    if v is None:
        return None

    if isinstance(v, str) and v.lower() in ['y', 'yes', 'true']:
        return True
    elif isinstance(v, str) and v.lower() in ['n', 'no', 'false']:
        return False
    else:
        return v


def _prettify_xml(file_path: str):
    dom = xml.dom.minidom.parse(file_path)
    pretty_xml_as_string = dom.toprettyxml()
    with open(file_path, 'w') as f:
        f.write(pretty_xml_as_string)


@pytest.fixture(autouse=True)
def count(request):
    """
    Enable parametrization for the same cli option. Inject to global variable `COUNT`.
    """
    global _COUNT
    _COUNT = _gte_one_int(getattr(request, 'param', request.config.option.count))


def parse_multi_dut_args(count: int, s: str) -> t.Any | tuple[t.Any]:
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


def multi_dut_argument(func) -> t.Callable[..., str | None | tuple[str | None]]:
    """
    Used for parse the multi-dut argument according to the `count` amount.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return parse_multi_dut_args(_COUNT, func(*args, **kwargs))

    return wrapper


def multi_dut_fixture(func) -> t.Callable[..., t.Any | tuple[t.Any]]:
    """
    Apply the multi-dut arguments to each fixture.

    Note:
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

            res = tuple([*list(res), func(*args, **current_kwargs)])

        return res

    return wrapper


def multi_dut_generator_fixture(
    func,
) -> t.Callable[..., t.Generator[t.Any | tuple[t.Any], t.Any, None]]:
    """
    Apply the multi-dut arguments to each fixture.

    Note:
        Run the `func()` for multiple times by iterating all `kwargs` via `itemgetter`. Auto call `close()` or
        `terminate()` method of the object after it yield back.

    Yields:
        The return value, if `count` is 1.
        The tuple of return values, if `count` is greater than 1.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        def _close_or_terminate(obj):
            if obj is None:
                del obj
                return

            try:
                if isinstance(obj, subprocess.Popen | multiprocessing.process.BaseProcess):
                    obj.terminate()
                    obj.kill()
                elif isinstance(obj, io.IOBase):
                    try:
                        obj.close()
                    except Exception as e:
                        logging.debug('file %s closed failed with error: %s', obj, str(e))
                else:
                    try:
                        obj.close()
                    except AttributeError:
                        try:
                            obj.terminate()
                        except AttributeError:
                            pass
                    except Exception as e:
                        logging.debug('Not properly caught object %s: %s', obj, str(e))
            except Exception as e:
                logging.debug('%s: %s', obj, str(e))
                return  # swallow up all error
            finally:
                referrers = gc.get_referrers(obj)
                for _referrer in referrers:
                    if isinstance(_referrer, list):
                        for _i, val in enumerate(_referrer):
                            if val is obj:
                                _referrer[_i] = None
                    elif isinstance(_referrer, dict):
                        for key, value in _referrer.items():
                            if value is obj:
                                _referrer[key] = None
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

                try:
                    i_res = func(*args, **current_kwargs)
                    res.append(i_res)
                except Exception:
                    for item in res:  # close the earlier succeeded set up items
                        _close_or_terminate(item)

                    raise

            try:
                yield res
            finally:
                if res:
                    for item in res:
                        _close_or_terminate(item)

    return wrapper


def _request_param_or_config_option_or_default(request: FixtureRequest, option: str, default: t.Any = None):
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
        Final value
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


@pytest.fixture
@multi_dut_argument
def logfile_extension(request: FixtureRequest) -> str:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'logfile_extension', '.log')


@pytest.fixture(scope='session')
def session_tempdir(request: FixtureRequest, session_root_logdir: str) -> str:
    """Session scoped temp dir for pytest-embedded"""
    _tmpdir = os.path.join(
        session_root_logdir,
        'pytest-embedded',
        utcnow_str(),
    )
    os.makedirs(_tmpdir, exist_ok=True)

    request.config.stash[_session_tempdir_key] = _tmpdir

    return _tmpdir


@pytest.fixture(scope='session')
def cache_dir(request: FixtureRequest) -> str:
    """Cache dir for pytest-embedded"""
    _cache_root_dir = os.path.realpath(
        _request_param_or_config_option_or_default(request, 'cache_dir', tempfile.gettempdir())
    )
    _cache_work_dir = os.path.join(_cache_root_dir, 'pytest-embedded', 'pytest-embedded-cache')
    os.makedirs(_cache_work_dir, exist_ok=True)
    return _cache_work_dir


@pytest.fixture(scope='session')
def port_target_cache(cache_dir) -> dict[str, str]:
    """Session scoped port-target cache, for esp only"""
    _cache_file_path = os.path.join(cache_dir, 'port_target_cache')
    lock = filelock.FileLock(f'{_cache_file_path}.lock')
    resp: dict[str, str] = {}
    with lock:
        try:
            with shelve.open(_cache_file_path) as f:
                resp = dict(f)
        except dbm.error:
            os.remove(_cache_file_path)

    yield resp
    with lock:
        with shelve.open(_cache_file_path) as f:
            for k, v in resp.items():
                f[k] = v


@pytest.fixture(scope='session')
def port_app_cache() -> dict[str, str]:
    """Session scoped port-app cache, for idf only"""
    return {}


@pytest.fixture(scope='session', autouse=True)
def _mp_manager():
    manager = MessageQueueManager()
    manager.start()

    global _MP_MANAGER
    _MP_MANAGER = manager

    yield manager

    manager.shutdown()


@pytest.fixture
def test_case_tempdir(test_case_name: str, session_tempdir: str) -> str:
    """Function scoped temp dir for pytest-embedded"""
    return os.path.join(session_tempdir, test_case_name)


@pytest.fixture
@multi_dut_fixture
def _meta(test_case_tempdir, port_target_cache, port_app_cache, logfile_extension) -> Meta:
    """function scoped _meta info"""
    return Meta(test_case_tempdir, port_target_cache, port_app_cache, logfile_extension)


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
def _pexpect_logfile(test_case_tempdir, logfile_extension, dut_index, dut_total) -> str:
    if dut_total > 1:
        name = f'dut-{dut_index}'
    else:
        name = 'dut'

    return os.path.join(test_case_tempdir, f'{name}{logfile_extension}')


@pytest.fixture
@multi_dut_generator_fixture
def msg_queue(_mp_manager) -> MessageQueue:  # kwargs passed by `multi_dut_generator_fixture()`
    return _mp_manager.MessageQueue()


@pytest.fixture
@multi_dut_argument
def with_timestamp(request: FixtureRequest) -> bool:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'with_timestamp', None)


@pytest.fixture
@multi_dut_generator_fixture
def _listener(msg_queue, _pexpect_logfile, with_timestamp, dut_index, dut_total) -> multiprocessing.Process:
    """
    The listener would create a `_listen` process. The `_listen` process would get the string from the message queue,
    and do two things together:

    1. print the string to `sys.stdout`
    2. write the string to `_pexpect_logfile`
    """
    return _listener_gn(**locals())


@pytest.fixture
@multi_dut_generator_fixture
def _pexpect_fr(_pexpect_logfile, _listener) -> t.BinaryIO:
    return _pexpect_fr_gn(**locals())


@pytest.fixture
# here we use @multi_dut_fixture
# otherwise the close() method would be called, and would raise the OSError
# The file descriptor would be closed at `_pexpect_fr`
@multi_dut_fixture
def pexpect_proc(_pexpect_fr) -> PexpectProcess:
    """Pexpect process that run the expect functions on"""
    return pexpect_proc_fn(**locals())


@pytest.fixture
@multi_dut_generator_fixture
def redirect(msg_queue: MessageQueue) -> t.Callable[..., contextlib.redirect_stdout]:
    """
    A context manager that could help duplicate all the `sys.stdout` to `msg_queue`.

    Examples:
        >>> with redirect():
        >>>    print('this should be logged and sent to pexpect_proc')
    """

    def _inner():
        return contextlib.redirect_stdout(msg_queue)

    return _inner


###############################
# CLI Option Related Fixtures #
###############################
########
# base #
########
@pytest.fixture
@multi_dut_argument
def embedded_services(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'embedded_services', None)


@pytest.fixture
@multi_dut_argument
def app_path(request: FixtureRequest, test_file_path: str, record_xml_attribute) -> str | None:
    """Enable parametrization for the same cli option"""
    res = _request_param_or_config_option_or_default(request, 'app_path', os.path.dirname(test_file_path))
    record_xml_attribute('app_path', res)
    return res


@pytest.fixture
@multi_dut_argument
def esp_flash_force(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'esp_flash_force', False)


@pytest.fixture
@multi_dut_argument
def build_dir(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'build_dir', 'build')


##########
# serial #
##########
@pytest.fixture
@multi_dut_argument
def port(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'port', None)


@pytest.fixture
@multi_dut_argument
def baud(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'baud', None)


@pytest.fixture
@multi_dut_argument
def port_location(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'port_location', None)


#######
# esp #
#######
@pytest.fixture
@multi_dut_argument
def target(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'target', None)


@pytest.fixture
@multi_dut_argument
def beta_target(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'beta_target', None)


@pytest.fixture
@multi_dut_argument
def flash_port(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'flash_port', None)


@pytest.fixture
@multi_dut_argument
def skip_autoflash(request: FixtureRequest) -> bool | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'skip_autoflash', None)


@pytest.fixture
@multi_dut_argument
def erase_all(request: FixtureRequest) -> bool | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'erase_all', None)


@pytest.fixture
@multi_dut_argument
def esptool_baud(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'esptool_baud', None)


@pytest.fixture
@multi_dut_argument
def port_mac(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'port_mac', None)


@pytest.fixture
@multi_dut_argument
def port_serial_number(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'port_serial_number', None)


#######
# idf #
#######
@pytest.fixture
@multi_dut_argument
def part_tool(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'part_tool', None)


@pytest.fixture
@multi_dut_argument
def confirm_target_elf_sha256(request: FixtureRequest) -> bool | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'confirm_target_elf_sha256', None)


@pytest.fixture
@multi_dut_argument
def erase_nvs(request: FixtureRequest) -> bool | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'erase_nvs', None)


@pytest.fixture
@multi_dut_argument
def skip_check_coredump(request: FixtureRequest) -> bool | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'skip_check_coredump', None)


@pytest.fixture
@multi_dut_argument
def panic_output_decode_script(request: FixtureRequest) -> bool | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'panic_output_decode_script', None)


########
# jtag #
########
@pytest.fixture
@multi_dut_argument
def gdb_prog_path(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'gdb_prog_path', None)


@pytest.fixture
@multi_dut_argument
def gdb_cli_args(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'gdb_cli_args', None)


@pytest.fixture
@multi_dut_argument
def no_gdb(request: FixtureRequest) -> bool:
    return _request_param_or_config_option_or_default(request, 'no_gdb', False)


@pytest.fixture
@multi_dut_argument
def openocd_prog_path(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'openocd_prog_path', None)


@pytest.fixture
@multi_dut_argument
def openocd_cli_args(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'openocd_cli_args', None)


########
# qemu #
########
@pytest.fixture
@multi_dut_argument
def qemu_image_path(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'qemu_image_path', None)


@pytest.fixture
@multi_dut_argument
def qemu_prog_path(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'qemu_prog_path', None)


@pytest.fixture
@multi_dut_argument
def qemu_cli_args(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'qemu_cli_args', None)


@pytest.fixture
@multi_dut_argument
def qemu_extra_args(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'qemu_extra_args', None)


@pytest.fixture
@multi_dut_argument
def qemu_efuse_path(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'qemu_efuse_path', None)


@pytest.fixture
@multi_dut_argument
def skip_regenerate_image(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'skip_regenerate_image', None)


@pytest.fixture
@multi_dut_argument
def encrypt(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'encrypt', None)


@pytest.fixture
@multi_dut_argument
def keyfile(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'keyfile', None)


#########
# Wokwi #
#########
@pytest.fixture
@multi_dut_argument
def wokwi_diagram(request: FixtureRequest) -> str | None:
    """Enable parametrization for the same cli option"""
    return _request_param_or_config_option_or_default(request, 'wokwi_diagram', None)


####################
# Private Fixtures #
####################
@pytest.fixture
@multi_dut_fixture
def _services(embedded_services: str | None) -> list[str]:
    if not embedded_services:
        return ['base']

    services = [s.strip() for s in embedded_services.split(',') if s]

    for s in services:
        if s not in SERVICE_LIB_NAMES.keys():
            raise UnknownServiceError(s)

        try:
            importlib.import_module(SERVICE_LIB_NAMES[s].replace('-', '_'))
        except ModuleNotFoundError:
            raise PackageNotInstalledError(s)

    return ['base', *services]


@pytest.fixture(autouse=True)
@multi_dut_fixture
def parametrize_fixtures(
    _services,
    # parametrize fixtures
    app_path,
    build_dir,
    port,
    port_serial_number,
    port_location,
    port_mac,
    target,
    beta_target,
    baud,
    flash_port,
    skip_autoflash,
    erase_all,
    esptool_baud,
    esp_flash_force,
    part_tool,
    confirm_target_elf_sha256,
    erase_nvs,
    skip_check_coredump,
    panic_output_decode_script,
    openocd_prog_path,
    openocd_cli_args,
    gdb_prog_path,
    gdb_cli_args,
    no_gdb,
    qemu_image_path,
    qemu_prog_path,
    qemu_cli_args,
    qemu_extra_args,
    qemu_efuse_path,
    wokwi_diagram,
    skip_regenerate_image,
    encrypt,
    keyfile,
    # common fixtures
    test_case_name,
    _meta,
):
    set_parametrized_fixtures_cache(locals())
    return locals()


@pytest.fixture(autouse=True)
def close_factory_duts():
    yield
    DutFactory.close()


@pytest.fixture
@multi_dut_fixture
def _fixture_classes_and_options(
    parametrize_fixtures,
    # pre-initialized fixtures
    dut_index,
    _pexpect_logfile,
    pexpect_proc,
    msg_queue,
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
    kwargs = locals()
    kwargs.update(kwargs.pop('parametrize_fixtures'))

    return _fixture_classes_and_options_fn(**kwargs)


####################
# Derived Fixtures #
####################
@pytest.fixture
@multi_dut_fixture
def app(_fixture_classes_and_options: ClassCliOptions) -> App:
    """A pytest fixture to gather information from the specified built binary folder"""
    return app_fn(**locals())


@pytest.fixture
@multi_dut_generator_fixture
def serial(_fixture_classes_and_options, msg_queue, app) -> t.Union['Serial', 'LinuxSerial'] | None:
    """A serial subprocess that could read/redirect/write"""
    return serial_gn(**locals())


@pytest.fixture
@multi_dut_generator_fixture
def openocd(_fixture_classes_and_options: ClassCliOptions) -> t.Optional['OpenOcd']:
    """An openocd subprocess that could read/redirect/write"""
    return openocd_gn(**locals())


@pytest.fixture
@multi_dut_generator_fixture
def gdb(_fixture_classes_and_options: ClassCliOptions) -> t.Optional['Gdb']:
    """A gdb subprocess that could read/redirect/write"""
    return gdb_gn(**locals())


@pytest.fixture
@multi_dut_generator_fixture
def qemu(_fixture_classes_and_options: ClassCliOptions, app) -> t.Optional['Qemu']:
    """A qemu subprocess that could read/redirect/write"""
    return qemu_gn(**locals())


@pytest.fixture
@multi_dut_generator_fixture
def wokwi(_fixture_classes_and_options: ClassCliOptions, app) -> t.Optional['Wokwi']:
    """A wokwi subprocess that could read/redirect/write"""
    return wokwi_gn(**locals())


@pytest.fixture
@multi_dut_generator_fixture
def dut(
    _fixture_classes_and_options: ClassCliOptions,
    openocd: t.Optional['OpenOcd'],
    gdb: t.Optional['Gdb'],
    app: App,
    serial: t.Union['Serial', 'LinuxSerial'] | None,
    qemu: t.Optional['Qemu'],
    wokwi: t.Optional['Wokwi'],
) -> Dut | list[Dut]:
    """
    A device under test (DUT) object that could gather output from various sources and redirect them to the pexpect
    process, and run `expect()` via its pexpect process.
    """
    return dut_gn(**locals())


@pytest.fixture
def unity_tester(dut: t.Union['IdfDut', tuple['IdfDut']]) -> t.Optional['CaseTester']:
    try:
        from pytest_embedded_idf import CaseTester, IdfDut
    except ImportError:
        yield None
    else:
        # all dut instance must be IdfDut to use this fixture
        for _dut in to_list(dut):
            if not isinstance(_dut, IdfDut):
                yield None

        yield CaseTester(to_list(dut))


##################
# Hook Functions #
##################
_junit_merger_key = pytest.StashKey['JunitMerger']()
_pytest_embedded_key = pytest.StashKey['PytestEmbedded']()
_session_tempdir_key = pytest.StashKey['session_tempdir']()
_junit_report_path_key = pytest.StashKey[str]()


def pytest_configure(config: Config) -> None:
    config.stash[_junit_merger_key] = JunitMerger(
        config.option.xmlpath, config.getoption('unity_test_report_mode', UnityTestReportMode.REPLACE.value)
    )
    config.stash[_junit_report_path_key] = config.option.xmlpath

    supported_targets_args = config.getoption('supported_targets', None)
    preview_targets_args = config.getoption('preview_targets', None)
    if supported_targets_args or preview_targets_args:
        from pytest_embedded_idf.utils import preview_targets, supported_targets

        if supported_targets_args is not None:
            supported_targets.set([_t.strip() for _t in supported_targets_args.split(',')])
        if preview_targets_args:
            preview_targets.set([_t.strip() for _t in preview_targets_args.split(',')])

    config.stash[_pytest_embedded_key] = PytestEmbedded(
        parallel_count=config.getoption('parallel_count'),
        parallel_index=config.getoption('parallel_index'),
        check_duplicates=config.getoption('check_duplicates', False),
        prettify_junit_report=_str_bool(config.getoption('prettify_junit_report', False)),
        add_target_as_marker_with_amount=_str_bool(config.getoption('add_target_as_marker_with_amount', False)),
    )
    config.pluginmanager.register(config.stash[_pytest_embedded_key])
    config.addinivalue_line('markers', 'skip_if_soc')


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
        check_duplicates: bool = False,
        prettify_junit_report: bool = False,
        add_target_as_marker_with_amount: bool = False,
    ):
        self.parallel_count = parallel_count
        self.parallel_index = parallel_index
        self.check_duplicates = check_duplicates
        self.prettify_junit_report = prettify_junit_report
        self.add_target_as_marker_with_amount = add_target_as_marker_with_amount

    @staticmethod
    def _raise_dut_failed_cases_if_exists(duts: t.Iterable[Dut]) -> None:
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
    def _duplicate_items(items: list[_T]) -> list[_T]:
        duplicates = []
        counter = Counter(items)
        for elem, cnt in counter.items():
            if cnt > 1:
                duplicates.append(elem)

        return duplicates

    @staticmethod
    def get_param(item: Function, key: str, default: t.Any = None) -> t.Any:
        # funcargs is not calculated while collection
        # callspec is something defined in parametrize
        if not hasattr(item, 'callspec'):
            return default

        return item.callspec.params.get(key, default) or default

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_collection_modifyitems(self, config: Config, items: list[Function]):
        # ------ add marker based on target ------
        if self.add_target_as_marker_with_amount:
            for item in items:
                item_target = self.get_param(item, 'target')
                if not item_target:
                    continue

                if not isinstance(item_target, str):
                    raise ValueError(f'`target` should be a string, got {type(item_target)} instead')

                # --add-target-as-marker-with-amount
                count = self.get_param(item, 'count', 1)
                _marker = targets_to_marker(to_list(parse_multi_dut_args(count, item_target)))

                item.add_marker(_marker)

        # ------ pytest.mark.skip_if_soc ------
        for item in items:
            skip_marker = item.get_closest_marker('skip_if_soc')
            if not skip_marker:
                continue
            if 'idf' not in map(str.strip, config.getoption('embedded_services').split(',')):
                raise ValueError("'skip_if_soc' marker must be used with the 'idf' embedded service.")

            from esp_bool_parser import parse_bool_expr

            target = config.getoption('--target', None)
            if hasattr(item, 'callspec'):
                target = item.callspec.params.get('target', None)
            if target == 'auto' or not isinstance(target, str):
                warnings.warn(
                    f"Ignoring pytest.mark.skip_if_soc for test item '{item.originalname}': "
                    "Ensure that 'target' is included in the test's "
                    "@pytest.mark.parametrize when using 'skip_if_soc', "
                    'or provide the --target argument '
                    "when running tests (excluding 'auto' and multi-DUT configurations)."
                )
                continue
            if '|' in target:
                warnings.warn(
                    'Ignoring pytest.mark.skip_if_soc, '
                    "because multi-DUT tests do not support the 'skip_if_soc' marker. "
                    'Please adjust the test setup accordingly.'
                )
                continue

            stm = parse_bool_expr(skip_marker.args[0])
            if stm.get_value(target, ''):
                reason = f'Filtered by {skip_marker.args[0]}, for {target}.'
                item.add_marker(pytest.mark.skip(reason=reason))

        yield

        if self.check_duplicates:
            duplicated_test_cases = self._duplicate_items([test.name for test in items])
            if duplicated_test_cases:
                raise ValueError(f'Duplicated test function names: {duplicated_test_cases}')

            duplicated_test_script_paths = self._duplicate_items(
                [os.path.basename(name) for name in set([str(test.path.absolute()) for test in items])]
            )
            if duplicated_test_script_paths:
                raise ValueError(f'Duplicated test scripts: {duplicated_test_script_paths}')

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
    def pytest_sessionfinish(self, session: Session, exitstatus: int) -> None:
        modifier: JunitMerger = session.config.stash[_junit_merger_key]
        _stash_session_tempdir = session.config.stash.get(_session_tempdir_key, None)
        _stash_junit_report_path = session.config.stash.get(_junit_report_path_key, None)
        if _stash_session_tempdir is not None:
            modifier.merge(sorted(find_by_suffix('.xml', _stash_session_tempdir)))

        if _stash_junit_report_path:
            # before we only modified the junit report generated by the unity test cases
            # now we do it again to check the python test cases
            with open(_stash_junit_report_path) as fr:
                file_str = fr.read()
            with open(_stash_junit_report_path, 'w') as fw:
                fw.write(escape_illegal_xml_chars(file_str))

            if self.prettify_junit_report:
                _prettify_xml(_stash_junit_report_path)

        exitstatus = int(modifier.failed)  # True -> 1  False -> 0  # noqa
