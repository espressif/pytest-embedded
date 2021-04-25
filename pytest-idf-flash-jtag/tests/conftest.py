import os

import pytest  # noqa

pytest_plugins = [
    'pytester',
]


@pytest.fixture
def test_root():
    return os.path.realpath(os.path.join(__file__, '..'))
