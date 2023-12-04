"""A pytest plugin that designed for embedded testing."""

from .app import App
from .dut import Dut

__all__ = ['App', 'Dut']

__version__ = '1.4.2'
