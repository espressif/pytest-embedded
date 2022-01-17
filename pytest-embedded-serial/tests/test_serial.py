import sys

import pytest


@pytest.mark.skipif(sys.platform == 'win32', reason='No socat support on windows')
def test_serial_port(testdir):
    testdir.makepyfile("""
        import pytest
        import subprocess

        @pytest.fixture(autouse=True)
        def open_tcp_port():
            proc = subprocess.Popen('socat TCP4-LISTEN:9876,fork EXEC:cat', shell=True)
            yield
            proc.terminate()

        def test_serial_port(dut):
            dut.write(b'hello world')
            dut.expect('hello world')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'serial',
        '--port', 'socket://localhost:9876',
    )

    result.assert_outcomes(passed=1)
