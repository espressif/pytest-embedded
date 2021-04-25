import pytest


def pytest_addoption(parser):
    group = parser.getgroup('app')
    group.addoption('--app-path')
    group.addoption('--target')


class DUT:
    pass


@pytest.fixture()
def dut():
    return DUT()
