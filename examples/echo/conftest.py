import subprocess

import pytest


@pytest.fixture(autouse=True)
def open_tcp_port():
    proc = subprocess.Popen('socat TCP4-LISTEN:9876,fork EXEC:cat', shell=True)
    yield
    proc.terminate()
