import os

import pytest

pytest_plugins = [
    'pytester',
]


@pytest.fixture(autouse=True)
def disable_autoload(testdir):
    testdir.monkeypatch.setenv('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')
    testdir.copy_example(os.path.join(os.path.dirname(__file__), 'tests', 'fixtures'))
    yield


@pytest.fixture
def test_root_dir():
    pass
