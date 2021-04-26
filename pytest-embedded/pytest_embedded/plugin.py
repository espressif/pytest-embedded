import pytest


def pytest_addoption(parser):
    group = parser.getgroup('app')
    group.addoption('--app-path')
    group.addoption('--target')


class DUT:
    pass


@pytest.fixture
def test_file_name(request):
    return request.module.__name__


@pytest.fixture
def test_case_name(request):
    return request.node.originalname


@pytest.fixture()
def dut():
    return DUT()
