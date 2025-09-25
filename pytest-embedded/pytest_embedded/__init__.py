"""A pytest plugin that designed for embedded testing."""

from .app import App
from .dut import Dut
from .dut_factory import DutFactory

__all__ = ['App', 'Dut', 'DutFactory']

__version__ = '2.1.0'
