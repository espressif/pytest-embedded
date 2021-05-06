import logging
import os
from collections import defaultdict

import pytest

from .app import App
from .dut import Dut


@pytest.fixture
def test_file_name(request):
    return request.module.__name__


@pytest.fixture
def test_case_name(request):
    return request.node.originalname


def pytest_addoption(parser):
    group = parser.getgroup('embedded')
    group.addoption('--app-path',
                    default=os.getcwd(),
                    help='App path')


KNOWN_OPTIONS = defaultdict(list)
KNOWN_OPTIONS['App'].append('app_path')


@pytest.fixture
def options(request):
    res = {}
    options = request.config.option.__dict__
    for group, opts in KNOWN_OPTIONS.items():
        res[group] = {}
        for opt in opts:
            if opt in options:
                res[group][opt] = options[opt]
    return res


@pytest.fixture
def app(options):
    app_options = options.get('App', {})
    logging.info(app_options)
    return App(**app_options)


@pytest.fixture
def dut(app, options):
    dut_options = options.get('DUT', {})
    logging.info(dut_options)
    dut = Dut(app=app, **dut_options)
    try:
        yield dut
    finally:
        dut.close()
