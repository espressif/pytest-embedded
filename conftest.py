import pytest

pytest_plugins = [
    'pytester',
]


@pytest.fixture(autouse=True)
def disable_autoload(testdir):
    testdir.monkeypatch.setenv('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')
    yield
