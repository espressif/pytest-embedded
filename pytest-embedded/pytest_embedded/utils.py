import dataclasses
import datetime
import functools
import importlib
import logging
import os
import re
import typing as t
from collections import defaultdict
from dataclasses import dataclass

if t.TYPE_CHECKING:
    from . import App

#############
# Constants #
#############
BASE_LIB_NAME = 'pytest-embedded'

SERVICE_LIB_NAMES = {
    'serial': f'{BASE_LIB_NAME}-serial',
    'esp': f'{BASE_LIB_NAME}-serial-esp',
    'idf': f'{BASE_LIB_NAME}-idf',
    'jtag': f'{BASE_LIB_NAME}-jtag',
    'qemu': f'{BASE_LIB_NAME}-qemu',
    'arduino': f'{BASE_LIB_NAME}-arduino',
    'wokwi': f'{BASE_LIB_NAME}-wokwi',
    'nuttx': f'{BASE_LIB_NAME}-nuttx',
}

FIXTURES_SERVICES = {
    'app': ['base', 'idf', 'qemu', 'arduino', 'nuttx'],
    'serial': ['serial', 'jtag', 'esp', 'idf', 'arduino', 'nuttx'],
    'openocd': ['jtag'],
    'gdb': ['jtag'],
    'qemu': ['qemu'],
    'wokwi': ['wokwi'],
    'dut': ['base', 'serial', 'jtag', 'qemu', 'idf', 'wokwi', 'nuttx'],
}


@dataclass
class ClassCliOptions:
    classes: dict[str, type]
    mixins: dict[str, list[type]]
    kwargs: dict[str, dict[str, t.Any]]


_T = t.TypeVar('_T')

_MIXIN_REQUIRED_SERVICES = {
    'IdfUnityMixin': ['idf'],
}

_MIXIN_REQUIRED_SERVICES_KEY = '_based_on_services'


#######################
# Errors and Warnings #
#######################
class UserHint(Warning):
    pass


class UnknownServiceError(SystemExit):
    def __init__(self, service: str) -> None:
        super().__init__(f'Unknown service "{service}". Valid options: {",".join(SERVICE_LIB_NAMES.keys())} ')


class PackageNotInstalledError(SystemExit):
    def __init__(self, service: str) -> None:
        super().__init__(
            f'Package {SERVICE_LIB_NAMES[service]} is not found but required by service {service}. '
            f'Please run "pip install -U {SERVICE_LIB_NAMES[service]}"'
        )


class RequireServiceError(SystemExit):
    def __init__(self, func_name: str, services: str | list[str]) -> None:
        services_str = ','.join(to_list(services))
        super().__init__(
            f'function {func_name} requires enabling one of the service(s) {services_str}. '
            f'Please enable by passing CLI options "--embedded-services {services_str}". '
            f'For more details, please refer to "pytest --help".'
        )


#####################
# Utility Functions #
#####################
def to_str(bytes_str: t.AnyStr) -> str:
    """
    Turn `bytes` or `str` to `str`

    Args:
        bytes_str: `bytes` or `str`

    Returns:
        utf8-decoded string
    """
    if isinstance(bytes_str, bytes):
        return bytes_str.decode('utf-8', errors='ignore')
    return bytes_str


def to_bytes(bytes_str: t.AnyStr, ending: t.AnyStr | None = None) -> bytes:
    """
    Turn `bytes` or `str` to `bytes`

    Args:
        bytes_str: `bytes` or `str`
        ending: `bytes` or `str`, will add to the end of the result.
            Only works when the `bytes_str` is `str`

    Returns:
        utf8-encoded bytes
    """
    if isinstance(bytes_str, str):
        bytes_str = bytes_str.encode()

        if ending:
            if isinstance(ending, str):
                ending = ending.encode()
            return bytes_str + ending

    return bytes_str


def to_list(s: _T) -> list[_T]:
    """
    Args:
        s: Anything

    Returns:
        List (list[_T])

        - `list(s)` (List. If `s` is a tuple or a set.
        - itself. If `s` is a list.
        - `[s]`. If `s` is other types.
    """
    if not s:
        return s

    if isinstance(s, set) or isinstance(s, tuple):
        return list(s)
    elif isinstance(s, list):
        return s
    else:
        return [s]


def find_by_suffix(suffix: str, path: str) -> list[str]:
    res = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(suffix):
                res.append(os.path.join(root, file))

    return res


def utcnow_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d_%H-%M-%S-%f')


_ANSI_COLOR_CODE_RE = re.compile(
    r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
""",
    re.VERBOSE,
)


def remove_asci_color_code(s: t.AnyStr) -> str:
    if isinstance(s, bytes):
        s = s.decode('utf-8', errors='ignore')
    return _ANSI_COLOR_CODE_RE.sub('', s)


@dataclasses.dataclass
class Meta:
    """
    Meta info for testing, session scope
    """

    logdir: str
    port_target_cache: dict[str, str]
    port_app_cache: dict[str, str]
    logfile_extension: str = '.log'

    def hit_port_target_cache(self, port: str, target: str) -> bool:
        if self.port_target_cache.get(port, None) == target:
            logging.debug('hit port-target cache: %s - %s', port, target)
            return True

        return False

    def set_port_target_cache(self, port: str, target: str) -> None:
        self.port_target_cache[port] = target
        logging.debug('set port-target cache: %s - %s', port, target)

    def drop_port_target_cache(self, port: str) -> None:
        try:
            self.port_target_cache.pop(port)
            logging.debug('drop port-target cache with port %s', port)
        except KeyError:
            logging.warning('no port-target cache with port %s', port)

    def hit_port_app_cache(self, port: str, app: 'App') -> bool:
        if self.port_app_cache.get(port, None) == app.binary_path:
            logging.debug('hit port-app cache: %s - %s', port, app.binary_path)
            return True

        return False

    def set_port_app_cache(self, port: str, app: 'App') -> None:
        self.port_app_cache[port] = app.binary_path
        logging.debug('set port-app cache: %s - %s', port, app.binary_path)

    def drop_port_app_cache(self, port: str) -> None:
        try:
            self.port_app_cache.pop(port)
            logging.debug('drop port-app cache with port %s', port)
        except KeyError:
            logging.warning('no port-app cache with port %s', port)


_ModuleType = type(importlib)


def lazy_load(
    base_module: _ModuleType, name_obj_dict: dict[str, t.Any], obj_module_dict: dict[str, str]
) -> t.Callable[[str], t.Any]:
    """
    use __getattr__ in the __init__.py file to lazy load some objects

    Args:
        base_module (ModuleType): base package module
        name_obj_dict (dict[str, any]): name, real object dict, used to store real objects,
            no need to add lazy-load objects
        obj_module_dict (dict[str, str]): dict of object name and module name

    Returns:
        __getattr__ function

    Example:

        ::

            __getattr__ = lazy_load(
                importlib.import_module(__name__),
                {
                    'IdfApp': IdfApp,
                    'LinuxDut': LinuxDut,
                    'LinuxSerial': LinuxSerial,
                    'CaseTester': CaseTester,
                },
                {
                    'IdfSerial': '.serial',
                    'IdfDut': '.dut',
                },
            )
    """

    def __getattr__(object_name):
        if object_name in name_obj_dict:
            return name_obj_dict[object_name]
        elif object_name in obj_module_dict:
            module = importlib.import_module(obj_module_dict[object_name], base_module.__name__)
            imported = getattr(module, object_name)
            name_obj_dict[object_name] = imported
            return imported
        else:
            raise AttributeError('Attribute %s not found in module %s', object_name, base_module.__name__)

    return __getattr__


class _InjectMixinMeta(type):
    def __call__(cls, *args, **kwargs):
        try:
            mixins = kwargs.pop('mixins', None)
            if mixins:
                mixins = to_list(mixins)
                name = cls.__name__ + 'With' + 'And'.join([m.__name__ for m in mixins])
                cls = type(name, tuple([*mixins, cls]), {})

                # users should only know concept "services", not mixins
                _based_on_services = set()
                for m in mixins:
                    if m.__name__ not in _MIXIN_REQUIRED_SERVICES:
                        continue

                    _based_on_services.update(to_list(_MIXIN_REQUIRED_SERVICES[m.__name__]))
                kwargs[_MIXIN_REQUIRED_SERVICES_KEY] = sorted(_based_on_services)
        except KeyError:
            pass
        return type.__call__(cls, *args, **kwargs)


class _InjectMixinCls(metaclass=_InjectMixinMeta):
    """
    This class provide a check function `require_services()` to check if the function is injected by
    enabling one of the required services.

    The benefits are:
    - provide the autocompletion for the functions provided by the mixins
    - check the requirement at runtime

    Example:

        ::

            class IdfUnityMixin:
                def foo(self):
                    print('foo from MixinOne')


            class Test(_InjectMixinCls):
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)

                @_InjectMixinCls.require_services('idf')
                def foo(self):
                    pass


            # mro(): TestWithIdfUnityMixin, IdfUnityMixin, Test, object
            s1 = Test(mixins=IdfUnityMixin)
            # mro(): Test, object
            s2 = Test()
            s1.foo()  # foo from IdfUnityMixin
            s2.foo()  # function foo requires enabling one of the service(s) idf.
    """

    def require_services(*services):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(self, *args, **kwargs):
                based = False
                for service in services:
                    if hasattr(self, _MIXIN_REQUIRED_SERVICES_KEY) and service in getattr(
                        self, _MIXIN_REQUIRED_SERVICES_KEY
                    ):
                        based = True
                        break

                if based:
                    return func(self, *args, **kwargs)
                else:
                    raise RequireServiceError(func.__name__, services)

            return wrapped

        return decorator


def targets_to_marker(targets: t.Iterable[str]) -> str:
    """
    Convert esp targets to pytest marker with amount, "+" for multiple targets types

    For example:
    - [esp32s2, esp32s2, esp32s3] -> esp32s2_2+esp32s3
    - [esp32] -> esp32
    - [esp32, esp32s2] -> esp32+esp32s2
    """
    t_amount = defaultdict(int)
    for target in sorted(targets):
        t_amount[target] += 1

    return '+'.join([f'{t}_{t_amount[t]}' if t_amount[t] > 1 else t for t in t_amount])
