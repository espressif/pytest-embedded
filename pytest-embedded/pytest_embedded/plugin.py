import logging
import os
from collections import defaultdict
from typing import Any, Callable, Dict

import pytest

from .app import App
from .dut import Dut
from .log import DuplicateStdout, PexpectProcess


@pytest.fixture
def test_file_path(request) -> str:
    """
    Returns:
         current test script file path
    """
    return request.module.__file__


@pytest.fixture
def test_case_name(request) -> str:
    """
    Returns:
        current test case function name
    """
    return request.node.originalname


def pytest_addoption(parser):
    group = parser.getgroup('embedded')
    group.addoption('--app-path', help='App path')


KNOWN_OPTIONS = defaultdict(list)  # For store known cli options
KNOWN_OPTIONS['App'].append('app_path')

ENV = {}  # For store env variables


@pytest.fixture
def options(request) -> Dict[str, Dict[str, Any]]:
    """
    Returns:
         dict which contains all the k-v pairs from `KNOWN_OPTIONS`
    """
    res = {}
    options = request.config.option.__dict__
    for group, opts in KNOWN_OPTIONS.items():
        res[group] = {}
        for opt in opts:
            if opt in options:
                res[group][opt] = options[opt]
    logging.info(res)
    return res


@pytest.fixture
def app(options, test_file_path) -> App:
    """
    Uses `options['App']` as kwargs to create instance.
    """
    app_options = options.get('App', {})
    if app_options['app_path'] is None:
        logging.info(f'test_file_path: {test_file_path}')
        app_options['app_path'] = os.path.dirname(test_file_path)
    return App(**app_options)


@pytest.fixture
def pexpect_proc() -> PexpectProcess:
    pexpect_proc = PexpectProcess()
    try:
        yield pexpect_proc
    finally:
        pexpect_proc.terminate()


@pytest.fixture
def dut(app, pexpect_proc, options) -> Dut:
    """
    Uses `options['Dut']` as kwargs to create instance.
    """
    dut_options = options.get('Dut', {})
    dut = Dut(app, pexpect_proc, **dut_options)
    try:
        yield dut
    finally:
        dut.close()


@pytest.fixture
def redirect(pexpect_proc) -> Callable[..., DuplicateStdout]:
    """
    Provided a context manager that could help log all the `sys.stdout` with pytest logging feature and redirect
    `sys.stdout` to `dut.pexpect_proc`.

    ```python
    with redirect('prefix'):
        print('this should be logged and sent to pexpect_proc')
    ```
    """

    def _inner(source=None):
        return DuplicateStdout(pexpect_proc, source=source)

    return _inner
