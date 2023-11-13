import sys

import pytest


def test_custom_serial_device(testdir):
    testdir.makepyfile(r"""
        import pytest

        def test_serial_mixed(dut):
            from pytest_embedded.dut_factory import DutFactory
            assert len(dut)==2
            another_dut = DutFactory.create()
            st = set(
                (
                    dut[0].serial.port,
                    dut[1].serial.port,
                    another_dut.serial.port
                )
            )
            assert len(st) == 3

        def test_custom_dut():
            from pytest_embedded.dut_factory import DutFactory
            another_dut = DutFactory.create(embedded_services='esp,serial')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,serial',
        '--count', 2,
    )
    result.assert_outcomes(passed=2, errors=0)


def test_custom_serial_device_dut_count_1(testdir):
    testdir.makepyfile(r"""
        import pytest

        def test_serial_device_created_dut_count_1(dut):
            from pytest_embedded.dut_factory import DutFactory
            another_dut = DutFactory.create()
            another_dut2 = DutFactory.create()
            st = set(
                (
                    dut.serial.port,
                    another_dut.serial.port,
                    another_dut2.serial.port
                )
            )
            assert len(st) == 3


    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,serial',
        '--count', 1,
    )
    result.assert_outcomes(passed=1, errors=0)


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
