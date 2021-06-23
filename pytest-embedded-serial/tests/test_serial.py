import os

import pytest

PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_serial',
]

serial_device_required = pytest.mark.skipif(os.getenv('DONT_SKIP_SERIAL_TESTS', False) is False,
                                            reason='after connected to espressif boards, '
                                                   'use "DONT_SKIP_SERIAL_TESTS" to run this test')


@serial_device_required
def test_serial_port(testdir):
    testdir.makepyfile("""
        import serial

        def test_serial_port(dut):
            assert type(dut.port_inst) == serial.Serial
            dut.expect('ESP-ROM')
    """)

    result = testdir.runpytest(
        *PLUGINS,
        '--port', '/dev/ttyUSB0',
    )

    result.assert_outcomes(passed=1)
