import logging
import os
from collections import defaultdict
from typing import Any, Callable, Dict

import pytest

from .app import App
from .dut import Dut
from .log import DuplicateLogStdout


@pytest.fixture
def test_file_path(request) -> str:
    """
    :return: current test script file path
    """
    return request.module.__file__


@pytest.fixture
def test_case_name(request) -> str:
    """
    :return: current test function name
    """
    return request.node.originalname


def pytest_addoption(parser):
    group = parser.getgroup('embedded')
    group.addoption('--app-path', help='App path')


KNOWN_OPTIONS = defaultdict(list)
KNOWN_OPTIONS['App'].append('app_path')


@pytest.fixture
def options(request) -> Dict[str, Dict[str, Any]]:
    """
    :return: dict which contains all the k-v pairs from :attr:`KNOWN_OPTIONS`
    """
    res = {}
    options = request.config.option.__dict__
    for group, opts in KNOWN_OPTIONS.items():
        res[group] = {}
        for opt in opts:
            if opt in options:
                res[group][opt] = options[opt]
    return res


@pytest.fixture
def app(options, test_file_path) -> App:
    """
    Uses :attr:`options['App']` as kwargs to create instance.

    :return: :class:`pytest_embedded.app.App` or derived class instance
    """
    app_options = options.get('App', {})
    if app_options['app_path'] is None:
        logging.info(f'test_file_path: {test_file_path}')
        app_options['app_path'] = os.path.dirname(test_file_path)
    logging.info(app_options)
    return App(**app_options)


@pytest.fixture
def dut(app, options) -> Dut:
    """
    Uses :attr:`options['Dut']` as kwargs to create instance.

    :return: :class:`pytest_embedded.dut.Dut` or derived class instance
    """
    dut_options = options.get('Dut', {})
    logging.info(dut_options)
    dut = Dut(app=app, **dut_options)
    try:
        yield dut
    finally:
        dut.close()


@pytest.fixture
def redirect(dut) -> Callable[..., DuplicateLogStdout]:
    """
    Provided a context manager that could help log all the ``sys.stdout`` with pytest logging feature and redirect
    ``sys.stdout`` to :attr:`dut.pexpect_proc`.

    :return: :class:`pytest_embedded.log.DuplicateLogStdout` instance
    """

    def _inner(source=None):
        return DuplicateLogStdout(dut.pexpect_proc, source=source)

    return _inner
