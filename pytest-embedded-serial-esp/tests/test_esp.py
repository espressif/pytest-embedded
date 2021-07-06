import os

import pytest

PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_serial',
    '-p', 'pytest_embedded_serial_esp',
]

serial_device_required = pytest.mark.skipif(os.getenv('DONT_SKIP_SERIAL_TESTS', False) is False,
                                            reason='after connected to espressif boards, '
                                                   'use "DONT_SKIP_SERIAL_TESTS" to run this test')


@serial_device_required
def test_detect_port(testdir):
    testdir.makepyfile("""
        def test_detect_port(dut):
            dut.expect('Detecting chip type...')
            assert dut.serial.target
            assert dut.serial.port
            dut.expect('Restarting now.')
    """)

    result = testdir.runpytest(
        *PLUGINS,
        '--target', 'esp32'
    )

    result.assert_outcomes(passed=1)
