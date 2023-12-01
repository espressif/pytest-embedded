import sys

import pytest


@pytest.mark.skipif(sys.platform == 'win32', reason='No socat support on windows')
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_serial_port(testdir):
    testdir.makepyfile(r"""
        import pytest
        import subprocess

        @pytest.fixture(autouse=True)
        def open_tcp_port():
            proc = subprocess.Popen('socat TCP4-LISTEN:9876,fork EXEC:cat', shell=True)
            yield
            proc.terminate()

        def test_serial_port(dut):
            dut.write(b'hello world\n')
            dut.expect('hello world')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'serial',
        '--port', 'socket://localhost:9876',
    )

    result.assert_outcomes(passed=1)


def test_teardown_called_for_multi_dut(testdir):
    testdir.makepyfile(r"""
        import pytest

        @pytest.mark.parametrize('count, embedded_services, port', [
            ('3', 'serial', '/dev/ttyUSB0|/dev/ttyUSB1|/dev/ttyUSB100'),  # set up failure
        ], indirect=True)
        def test_teardown_called_for_multi_dut_fail(dut):
            assert len(dut) == 3

        @pytest.mark.parametrize('count, embedded_services, port', [
            ('3', 'serial', '/dev/ttyUSB0|/dev/ttyUSB1|/dev/ttyUSB2'),  # set up succeeded
        ], indirect=True)
        def test_teardown_called_for_multi_dut_succeeded(dut):
            assert dut[0].serial.port == '/dev/ttyUSB0'
            assert dut[1].serial.port == '/dev/ttyUSB1'
            assert dut[2].serial.port == '/dev/ttyUSB2'
    """)

    result = testdir.runpytest()
    result.assert_outcomes(passed=1, errors=1)
