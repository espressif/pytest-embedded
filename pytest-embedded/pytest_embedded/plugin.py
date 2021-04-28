import os

import pytest

from .app import App
from .dut import DUT


def pytest_addoption(parser):
    group = parser.getgroup('app')
    group.addoption('--app-path',
                    default=os.getcwd(),
                    help='App path')
    group.addoption('--port',
                    default='/dev/ttyUSB1',
                    help='serial port')
    group.addoption('--part-tool',
                    help='Partition tool path, used for parsing partition table')


@pytest.fixture
def test_file_name(request):
    return request.module.__name__


@pytest.fixture
def test_case_name(request):
    return request.node.originalname


@pytest.fixture
def app(request):
    return App(app_path=request.config.getoption('app_path'),
               parttool=request.config.getoption('part_tool'))


@pytest.fixture
def dut(app, request):
    dut = DUT(app=app, port=request.config.getoption('port'))
    try:
        yield dut
    finally:
        dut.close()
