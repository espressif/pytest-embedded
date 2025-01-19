import datetime
import gc
import io
import logging
import multiprocessing
import os
import subprocess
import sys
import time
import typing as t
from collections import defaultdict
from pathlib import Path

if t.TYPE_CHECKING:
    from pytest_embedded_idf import LinuxSerial
    from pytest_embedded_idf.dut import IdfDut
    from pytest_embedded_jtag import Gdb, OpenOcd
    from pytest_embedded_qemu import Qemu
    from pytest_embedded_serial import Serial
    from pytest_embedded_wokwi import WokwiCLI

from . import App, Dut
from .log import MessageQueue, PexpectProcess
from .utils import FIXTURES_SERVICES, ClassCliOptions, to_str


def _drop_none_kwargs(kwargs: t.Dict[t.Any, t.Any]):
    return {k: v for k, v in kwargs.items() if v is not None}


if sys.platform == 'darwin':
    _ctx = multiprocessing.get_context('fork')
else:
    _ctx = multiprocessing.get_context()

_stdout = sys.__stdout__


# This variable is used to keep track of the number of DUTs created.
DUT_GLOBAL_INDEX = 0


# This variable holds values that were used in 'parametrize_fixtures'.
# It helps to obtain the necessary information for a custom DUT, such as '_meta', '_services', and 'test_case_name'.
PARAMETRIZED_FIXTURES_CACHE = {}


def msg_queue_gn() -> MessageQueue:
    return MessageQueue()


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
        _s = _s.replace('\r\n', '\n')  # remove extra \r. since multi-dut \r would mess up the log
        _s = _s.replace('\n', '\n' + prefix)
        if prefix and _s.endswith(prefix):
            _s = _s.rsplit(prefix, maxsplit=1)[0]
            _added_prefix = False

        _stdout.write(_s)
        _stdout.flush()
        time.sleep(0.1)


def _listener_gn(msg_queue, _pexpect_logfile, with_timestamp, dut_index, dut_total) -> multiprocessing.Process:
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
    )


def _pexpect_fr_gn(_pexpect_logfile, _listener) -> t.BinaryIO:
    Path(_pexpect_logfile).touch()
    _listener.start()
    return open(_pexpect_logfile, 'rb')


def pexpect_proc_fn(_pexpect_fr) -> PexpectProcess:
    return PexpectProcess(_pexpect_fr)


def _fixture_classes_and_options_fn(
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
    wokwi_cli_path,
    wokwi_timeout,
    wokwi_scenario,
    wokwi_diagram,
    skip_regenerate_image,
    encrypt,
    keyfile,
    # pre-initialized fixtures
    dut_index,
    _pexpect_logfile,
    test_case_name,
    pexpect_proc,
    msg_queue,
    _meta,
    **kwargs,
) -> ClassCliOptions:
    classes: t.Dict[str, type] = {}
    mixins: t.Dict[str, t.List[type]] = defaultdict(list)
    kwargs: t.Dict[str, t.Dict[str, t.Any]] = defaultdict(dict)

    for fixture in FIXTURES_SERVICES.keys():
        if fixture == 'app':
            kwargs['app'] = {'app_path': app_path, 'build_dir': build_dir}
            if 'idf' in _services:
                if 'qemu' in _services:
                    from pytest_embedded_qemu import DEFAULT_IMAGE_FN, QemuApp

                    classes[fixture] = QemuApp
                    kwargs[fixture].update({
                        'msg_queue': msg_queue,
                        'part_tool': part_tool,
                        'qemu_image_path': qemu_image_path,
                        'skip_regenerate_image': skip_regenerate_image,
                        'encrypt': encrypt,
                        'keyfile': keyfile,
                        'qemu_prog_path': qemu_prog_path,
                    })
                else:
                    from pytest_embedded_idf import IdfApp

                    classes[fixture] = IdfApp
                    kwargs[fixture].update({
                        'part_tool': part_tool,
                    })
            elif 'arduino' in _services:
                from pytest_embedded_arduino import ArduinoApp

                classes[fixture] = ArduinoApp
            elif 'nuttx' in _services and 'esp' in _services:
                from pytest_embedded_nuttx import NuttxApp

                classes[fixture] = NuttxApp
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
                    'esp_flash_force': esp_flash_force,
                    'flash_port': flash_port,
                    'skip_autoflash': skip_autoflash,
                    'erase_all': erase_all,
                    'meta': _meta,
                }
                if 'idf' in _services:
                    from pytest_embedded_idf import IdfSerial

                    classes[fixture] = IdfSerial
                    kwargs[fixture].update({
                        'app': None,
                        'confirm_target_elf_sha256': confirm_target_elf_sha256,
                        'erase_nvs': erase_nvs,
                    })
                elif 'arduino' in _services:
                    from pytest_embedded_arduino import ArduinoSerial

                    classes[fixture] = ArduinoSerial
                    kwargs[fixture].update({
                        'app': None,
                    })
                elif 'nuttx' in _services:
                    from pytest_embedded_nuttx import NuttxSerial

                    classes[fixture] = NuttxSerial
                    kwargs[fixture].update({
                        'app': None,
                        'baud': int(baud or NuttxSerial.SERIAL_BAUDRATE),
                        'esptool_baud': int(os.getenv('ESPBAUD') or esptool_baud or NuttxSerial.FLASH_BAUDRATE),
                    })
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
                elif not no_gdb:
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
                from pytest_embedded_qemu import (
                    DEFAULT_IMAGE_FN,
                    ENCRYPTED_IMAGE_FN,
                    Qemu,
                )

                classes[fixture] = Qemu
                kwargs[fixture] = {
                    'msg_queue': msg_queue,
                    'qemu_image_path': qemu_image_path
                    or os.path.join(
                        app_path or '', build_dir or 'build', ENCRYPTED_IMAGE_FN if encrypt else DEFAULT_IMAGE_FN
                    ),
                    'qemu_prog_path': qemu_prog_path,
                    'qemu_cli_args': qemu_cli_args,
                    'qemu_extra_args': qemu_extra_args,
                    'app': None,
                    'meta': _meta,
                    'dut_index': dut_index,
                }
        elif fixture == 'wokwi':
            if 'wokwi' in _services:
                from pytest_embedded_wokwi import WokwiCLI

                classes[fixture] = WokwiCLI
                kwargs[fixture].update({
                    'wokwi_cli_path': wokwi_cli_path,
                    'wokwi_timeout': wokwi_timeout,
                    'wokwi_scenario': wokwi_scenario,
                    'wokwi_diagram': wokwi_diagram,
                    'msg_queue': msg_queue,
                    'app': None,
                    'meta': _meta,
                    'firmware_resolver': None,
                })
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
            if 'idf' in _services and 'esp' not in _services:
                # esp,idf will use IdfDut, which based on IdfUnityDutMixin already
                from pytest_embedded_idf.unity_tester import IdfUnityDutMixin

                mixins[fixture].append(IdfUnityDutMixin)

            if 'wokwi' in _services:
                from pytest_embedded_wokwi import WokwiDut

                classes[fixture] = WokwiDut
                kwargs[fixture].update({
                    'wokwi': None,
                })

                if 'idf' in _services:
                    from pytest_embedded_wokwi.idf import IDFFirmwareResolver

                    kwargs['wokwi'].update({'firmware_resolver': IDFFirmwareResolver()})
                elif 'arduino' in _services:
                    from pytest_embedded_wokwi.arduino import ArduinoFirmwareResolver

                    kwargs['wokwi'].update({'firmware_resolver': ArduinoFirmwareResolver()})
                else:
                    raise SystemExit('wokwi service should be used together with idf or arduino service')
            elif 'qemu' in _services:
                if 'nuttx' in _services:
                    from pytest_embedded_nuttx import NuttxQemuDut

                    classes[fixture] = NuttxQemuDut
                    kwargs[fixture].update({
                        'qemu': None,
                    })
                else:
                    from pytest_embedded_qemu import QemuDut

                    classes[fixture] = QemuDut
                    kwargs[fixture].update({
                        'qemu': None,
                    })
            elif 'jtag' in _services:
                if 'idf' in _services:
                    from pytest_embedded_idf import IdfDut

                    classes[fixture] = IdfDut
                else:
                    from pytest_embedded_serial import SerialDut

                    classes[fixture] = SerialDut

                kwargs[fixture].update({
                    'serial': None,
                    'openocd': None,
                    'gdb': None,
                })
            elif 'serial' in _services or 'esp' in _services:
                if 'esp' in _services and 'idf' in _services:
                    from pytest_embedded_idf import IdfDut

                    classes[fixture] = IdfDut
                    kwargs[fixture].update({
                        'skip_check_coredump': skip_check_coredump,
                        'panic_output_decode_script': panic_output_decode_script,
                    })
                elif 'esp' in _services and 'nuttx' in _services:
                    from pytest_embedded_nuttx import NuttxEspDut

                    classes[fixture] = NuttxEspDut
                    kwargs[fixture].update({
                        'serial': None,
                    })
                elif 'nuttx' in _services:
                    from pytest_embedded_nuttx import NuttxSerialDut

                    classes[fixture] = NuttxSerialDut
                    kwargs[fixture].update({
                        'serial': None,
                    })
                else:
                    from pytest_embedded_serial import SerialDut

                    classes[fixture] = SerialDut

                kwargs[fixture].update({
                    'serial': None,
                })

    return ClassCliOptions(classes, mixins, kwargs)


def app_fn(_fixture_classes_and_options: ClassCliOptions) -> App:
    cls = _fixture_classes_and_options.classes['app']
    kwargs = _fixture_classes_and_options.kwargs['app']
    return cls(**_drop_none_kwargs(kwargs))


def serial_gn(_fixture_classes_and_options, msg_queue, app) -> t.Optional[t.Union['Serial', 'LinuxSerial']]:
    if hasattr(app, 'target') and app.target == 'linux':
        from pytest_embedded_idf import LinuxSerial

        cls = LinuxSerial
        kwargs = {
            'app': app,
            'msg_queue': msg_queue,
        }
        return cls(**kwargs)

    if 'serial' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['serial']
    kwargs = _fixture_classes_and_options.kwargs['serial']
    if 'app' in kwargs and kwargs['app'] is None:
        kwargs['app'] = app

    if kwargs.get('flash_port'):
        operation_port = kwargs.pop('port', None)
        if operation_port is None:
            raise SystemExit('If the flash port was set up, the port should also be set up.')

        flash_port = kwargs.pop('flash_port')
        kwargs['stop_after_init'] = True
        kwargs['port'] = flash_port
        flash_serial = cls(**_drop_none_kwargs(kwargs))
        time.sleep(3)  # time for device restart
        kwargs['stop_after_init'] = False
        kwargs['port'] = operation_port
        kwargs['skip_autoflash'] = True
        kwargs['ports_to_occupy'] = [flash_serial.port]

    return cls(**_drop_none_kwargs(kwargs))


def openocd_gn(_fixture_classes_and_options: ClassCliOptions) -> t.Optional['OpenOcd']:
    if 'openocd' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['openocd']
    kwargs = _fixture_classes_and_options.kwargs['openocd']
    return cls(**_drop_none_kwargs(kwargs))


def gdb_gn(_fixture_classes_and_options: ClassCliOptions) -> t.Optional['Gdb']:
    if 'gdb' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['gdb']
    kwargs = _fixture_classes_and_options.kwargs['gdb']
    return cls(**_drop_none_kwargs(kwargs))


def qemu_gn(_fixture_classes_and_options: ClassCliOptions, app) -> t.Optional['Qemu']:
    if 'qemu' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['qemu']
    kwargs = _fixture_classes_and_options.kwargs['qemu']

    if 'app' in kwargs and kwargs['app'] is None:
        kwargs['app'] = app

    return cls(**_drop_none_kwargs(kwargs))


def wokwi_gn(_fixture_classes_and_options: ClassCliOptions, app) -> t.Optional['WokwiCLI']:
    """A wokwi subprocess that could read/redirect/write"""
    if 'wokwi' not in _fixture_classes_and_options.classes:
        return None

    cls = _fixture_classes_and_options.classes['wokwi']
    kwargs = _fixture_classes_and_options.kwargs['wokwi']

    if 'app' in kwargs and kwargs['app'] is None:
        kwargs['app'] = app
    return cls(**_drop_none_kwargs(kwargs))


def dut_gn(
    _fixture_classes_and_options: ClassCliOptions,
    openocd: t.Optional['OpenOcd'],
    gdb: t.Optional['Gdb'],
    app: App,
    serial: t.Optional[t.Union['Serial', 'LinuxSerial']],
    qemu: t.Optional['Qemu'],
    wokwi: t.Optional['WokwiCLI'],
) -> t.Union[Dut, t.List[Dut]]:
    global DUT_GLOBAL_INDEX
    DUT_GLOBAL_INDEX += 1

    kwargs = _fixture_classes_and_options.kwargs['dut']
    mixins = _fixture_classes_and_options.mixins['dut']

    # since there's no way to know the target before setup finished
    # we have to use the `app.target` to determine the dut class here
    if hasattr(app, 'target') and app.target == 'linux':
        from pytest_embedded_idf import LinuxDut

        cls = LinuxDut
        kwargs['serial'] = None  # replace it later with LinuxSerial
    else:
        cls = _fixture_classes_and_options.classes['dut']

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
            elif k == 'wokwi':
                kwargs[k] = wokwi
    return cls(**_drop_none_kwargs(kwargs), mixins=mixins)


def set_parametrized_fixtures_cache(values: t.Dict):
    global PARAMETRIZED_FIXTURES_CACHE
    PARAMETRIZED_FIXTURES_CACHE = values.copy()


def _close_or_terminate(obj):
    if obj is None:
        del obj
        return

    try:
        if isinstance(obj, (subprocess.Popen, multiprocessing.process.BaseProcess)):
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


class DutFactory:
    # ruff: noqa: ERA001
    # Stores the objects that required by each dut
    # [
    #    [openocd, gdb, serial, qemu, wokwi, dut]  # dut-0
    #    [openocd, gdb, serial, qemu, wokwi, dut]  # dut-1
    #    ...
    # ]
    obj_stack: t.ClassVar[t.List[t.List[t.Any]]] = []

    @classmethod
    def close(cls):
        global DUT_GLOBAL_INDEX
        DUT_GLOBAL_INDEX = 0
        if hasattr(cls, 'obj_stack'):
            while cls.obj_stack:
                layout = DutFactory.obj_stack.pop()
                while layout:
                    obj = layout.pop()
                    _close_or_terminate(obj)
                del layout
            del DutFactory.obj_stack
        cls.obj_stack = []

    @classmethod
    def unity_tester(cls, *args: 'IdfDut'):
        from pytest_embedded_idf import CaseTester

        return CaseTester(args)

    @classmethod
    def create(
        cls,
        *,
        embedded_services: str = '',
        app_path: str = '',
        build_dir: str = 'build',
        port: t.Optional[str] = None,
        port_location: t.Optional[str] = None,
        port_mac: t.Optional[str] = None,
        target: t.Optional[str] = None,
        beta_target: t.Optional[str] = None,
        baud: t.Optional[int] = None,
        flash_port: t.Optional[str] = None,
        skip_autoflash: t.Optional[bool] = None,
        erase_all: t.Optional[bool] = None,
        esptool_baud: t.Optional[int] = None,
        esp_flash_force: t.Optional[bool] = False,
        part_tool: t.Optional[str] = None,
        confirm_target_elf_sha256: t.Optional[bool] = None,
        erase_nvs: t.Optional[bool] = None,
        skip_check_coredump: t.Optional[bool] = None,
        panic_output_decode_script: t.Optional[str] = None,
        openocd_prog_path: t.Optional[str] = None,
        openocd_cli_args: t.Optional[str] = None,
        gdb_prog_path: t.Optional[str] = None,
        gdb_cli_args: t.Optional[str] = None,
        no_gdb: t.Optional[bool] = None,
        qemu_image_path: t.Optional[str] = None,
        qemu_prog_path: t.Optional[str] = None,
        qemu_cli_args: t.Optional[str] = None,
        qemu_extra_args: t.Optional[str] = None,
        wokwi_cli_path: t.Optional[str] = None,
        wokwi_timeout: t.Optional[int] = 0,
        wokwi_scenario: t.Optional[str] = None,
        wokwi_diagram: t.Optional[str] = None,
        skip_regenerate_image: t.Optional[bool] = None,
        encrypt: t.Optional[bool] = None,
        keyfile: t.Optional[str] = None,
    ):
        """
        Create a Device Under Test (DUT) object with customizable parameters.

        Note:
            If you want to add an additional 'arg' parameter here, you also need to change plugin.py.
            Steps to add an argument:
            1. (plugin.py) Create a fixture to read the argument value.
            2. (plugin.py) Add the argument to parametrize_fixtures.
            3. (dut_factory.py) Add it to _fixture_classes_and_options_fn.
            4. (dut_factory.py) Add it to DutFactory.create.

        Args:
            embedded_services: Comma-separated list of embedded services.
            app_path: Path to the application.
            build_dir: Directory for build output (default is 'build').
            port: Port configuration.
            port_location: Port location.
            port_mac: Port MAC address.
            target: Target configuration.
            beta_target: Beta target configuration.
            baud: Baud rate.
            flash_port: Port used for flashing the app.
            skip_autoflash: Skip autoflash flag.
            erase_all: Erase all flag.
            esptool_baud: ESP tool baud rate.
            esp_flash_force: ESP flash force flag.
            part_tool: Part tool configuration.
            confirm_target_elf_sha256: Confirm target ELF SHA256.
            erase_nvs: Erase NVS flag.
            skip_check_coredump: Skip coredump check flag.
            panic_output_decode_script: Panic output decode script.
            openocd_prog_path: OpenOCD program path.
            openocd_cli_args: OpenOCD CLI arguments.
            gdb_prog_path: GDB program path.
            gdb_cli_args: GDB CLI arguments.
            no_gdb: No GDB flag.
            qemu_image_path: QEMU image path.
            qemu_prog_path: QEMU program path.
            qemu_cli_args: QEMU CLI arguments.
            qemu_extra_args: Additional QEMU arguments.
            wokwi_cli_path: Wokwi CLI path.
            wokwi_timeout: Wokwi timeout.
            wokwi_scenario: Wokwi scenario path.
            wokwi_diagram: Wokwi diagram path.
            skip_regenerate_image: Skip image regeneration flag.
            encrypt: Encryption flag.
            keyfile: Keyfile for encryption.

        Returns:
            DUT object: The created Device Under Test object.

        Examples:
            >>> foo = DutFactory.create(embedded_services='idf,esp', app_path='path_to_hello_world')
            >>> foo.expect_exact('Hello world!')
        """
        layout = []
        try:
            global PARAMETRIZED_FIXTURES_CACHE
            msg_queue = msg_queue_gn()
            layout.append(msg_queue)

            _pexpect_logfile = os.path.join(
                PARAMETRIZED_FIXTURES_CACHE['_meta'].logdir, f'custom-dut-{DUT_GLOBAL_INDEX}.txt'
            )
            logging.debug('You can get your custom DUT log file at the following path: %s.', _pexpect_logfile)

            _listener = _listener_gn(msg_queue, _pexpect_logfile, True, DUT_GLOBAL_INDEX, DUT_GLOBAL_INDEX + 1)
            layout.append(_listener)

            _pexpect_fr = _pexpect_fr_gn(_pexpect_logfile, _listener)
            layout.append(_pexpect_fr)

            pexpect_proc = pexpect_proc_fn(_pexpect_fr)

            _kwargs = {
                '_services': embedded_services or PARAMETRIZED_FIXTURES_CACHE['_services'],
                # parametrize fixtures
                'app_path': app_path,
                'build_dir': build_dir,
                'port': port,
                'port_location': port_location,
                'port_mac': port_mac,
                'target': target,
                'beta_target': beta_target,
                'baud': baud,
                'flash_port': flash_port,
                'skip_autoflash': skip_autoflash,
                'erase_all': erase_all,
                'esptool_baud': esptool_baud,
                'esp_flash_force': esp_flash_force,
                'part_tool': part_tool,
                'confirm_target_elf_sha256': confirm_target_elf_sha256,
                'erase_nvs': erase_nvs,
                'skip_check_coredump': skip_check_coredump,
                'panic_output_decode_script': panic_output_decode_script,
                'openocd_prog_path': openocd_prog_path,
                'openocd_cli_args': openocd_cli_args,
                'gdb_prog_path': gdb_prog_path,
                'gdb_cli_args': gdb_cli_args,
                'no_gdb': no_gdb,
                'qemu_image_path': qemu_image_path,
                'qemu_prog_path': qemu_prog_path,
                'qemu_cli_args': qemu_cli_args,
                'qemu_extra_args': qemu_extra_args,
                'wokwi_cli_path': wokwi_cli_path,
                'wokwi_timeout': wokwi_timeout,
                'wokwi_scenario': wokwi_scenario,
                'wokwi_diagram': wokwi_diagram,
                'skip_regenerate_image': skip_regenerate_image,
                'encrypt': encrypt,
                'keyfile': keyfile,
                # common
                'test_case_name': PARAMETRIZED_FIXTURES_CACHE['test_case_name'],
                '_meta': PARAMETRIZED_FIXTURES_CACHE['_meta'],
                # pre-initialized fixtures
                'dut_index': DUT_GLOBAL_INDEX,
                '_pexpect_logfile': _pexpect_logfile,
                'pexpect_proc': pexpect_proc,
                'msg_queue': msg_queue,
            }

            _fixture_classes_and_options = _fixture_classes_and_options_fn(**_kwargs)

            app = app_fn(_fixture_classes_and_options)

            openocd = openocd_gn(_fixture_classes_and_options)
            layout.append(openocd)

            gdb = gdb_gn(_fixture_classes_and_options)
            layout.append(gdb)

            serial = serial_gn(_fixture_classes_and_options, msg_queue, app)
            layout.append(serial)

            qemu = qemu_gn(_fixture_classes_and_options, app)
            layout.append(qemu)

            wokwi = wokwi_gn(_fixture_classes_and_options, app)
            layout.append(wokwi)

            dut = dut_gn(_fixture_classes_and_options, openocd, gdb, app, serial, qemu, wokwi)
            layout.append(dut)

            cls.obj_stack.append(layout)
            return dut

        except Exception as e:
            while layout:
                obj = layout.pop()
                _close_or_terminate(obj)
            del layout
            raise e
