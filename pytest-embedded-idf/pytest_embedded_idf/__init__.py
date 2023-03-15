import importlib

from pytest_embedded.utils import lazy_load

from .app import IdfApp
from .linux import LinuxDut, LinuxSerial
from .unity_tester import CaseTester

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


__all__ = [
    'IdfApp',
    'IdfSerial',
    'IdfDut',
    'CaseTester',
    'LinuxSerial',
    'LinuxDut',
]
