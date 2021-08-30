import os

import pytest

pytest_plugins = [
    'pytester',
]


@pytest.fixture(autouse=True)
def copy_fixtures(testdir):
    testdir.copy_example(os.path.join(os.path.dirname(__file__), 'tests', 'fixtures'))
    yield
