import os
import sys
from distutils.dir_util import copy_tree
from typing import List, Pattern

import pytest
from _pytest.config import Config
from _pytest.fixtures import FixtureRequest

pytest_plugins = [
    'pytester',
]


@pytest.fixture(autouse=True)
def copy_fixtures(testdir):
    copy_tree(os.path.join(os.path.dirname(__file__), 'tests', 'fixtures'), str(testdir.tmpdir))
    yield


@pytest.fixture(autouse=True)
def cache_file_remove(cache_dir):
    yield
    _cache_file_path = os.path.join(cache_dir, 'port_target_cache')
    if os.path.exists(_cache_file_path):
        os.remove(_cache_file_path)


@pytest.fixture
def first_index_of_messages():
    def _fake(_pattern: Pattern, _messages: List[str], _start: int = 0) -> int:
        for i, _message in enumerate(_messages):
            if _pattern.match(_message) and i >= _start:
                return i

        raise AssertionError(f'Not found {_pattern.pattern}')

    return _fake


@pytest.fixture(autouse=True)
def temp_disable_packages(monkeypatch, request: FixtureRequest):
    temp_marker = request.node.get_closest_marker('temp_disable_packages')
    if not temp_marker:
        return

    packages = temp_marker.args
    for name in list(sys.modules):
        if name in packages or name.split('.')[0] in packages:
            monkeypatch.setitem(sys.modules, name, None)


def pytest_configure(config: Config) -> None:
    for name, description in {'temp_disable_packages': 'disable packages in function scope'}.items():
        config.addinivalue_line('markers', f'{name}: {description}')
