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
        '--embedded-services',
        'esp,serial',
        '--count',
        2,
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
        '--embedded-services',
        'esp,serial',
        '--count',
        1,
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
        '--embedded-services',
        'serial',
        '--port',
        'socket://localhost:9876',
    )

    result.assert_outcomes(passed=1)


@pytest.mark.skipif(sys.platform == 'win32', reason='No pty support on windows')
def test_dut_teardown_releases_threads_and_port(testdir):
    import os
    import pty

    master_fd, slave_fd = pty.openpty()
    port = os.ttyname(slave_fd)
    try:
        testdir.makeconftest(r"""
            import pytest
            from pytest_embedded_serial.serial import Serial

            resources = ()

            @pytest.fixture
            def capture_resources(dut, _listener):
                global resources
                resources = (dut.serial, _listener)

            @pytest.hookimpl(trylast=True)
            def pytest_fixture_post_finalizer(fixturedef, request):
                if fixturedef.argname != 'msg_queue' or not resources:
                    return

                serial, listener = resources
                assert not listener.is_alive()
                assert serial._redirect_thread is not None
                assert not serial._redirect_thread.is_alive()
                assert not serial.proc.is_open
                assert serial.port not in Serial.occupied_ports
        """)
        testdir.makepyfile(r"""
            def test_dut_teardown(dut, capture_resources):
                assert dut.serial._redirect_thread.is_alive()
        """)

        result = testdir.runpytest('-s', '--embedded-services', 'serial', '--port', port)
        result.assert_outcomes(passed=1, errors=0)
    finally:
        os.close(master_fd)
        os.close(slave_fd)


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
