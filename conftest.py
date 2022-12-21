import os
from distutils.dir_util import copy_tree
from typing import List, Pattern

import pytest

pytest_plugins = [
    'pytester',
]


@pytest.fixture(autouse=True)
def copy_fixtures(testdir):
    copy_tree(os.path.join(os.path.dirname(__file__), 'tests', 'fixtures'), str(testdir.tmpdir))
    yield


@pytest.fixture
def first_index_of_messages():
    def _fake(_pattern: Pattern, _messages: List[str], _start: int = 0) -> int:
        for i, _message in enumerate(_messages):
            if _pattern.match(_message) and i >= _start:
                return i

        raise AssertionError(f'Not found {_pattern.pattern}')

    return _fake
