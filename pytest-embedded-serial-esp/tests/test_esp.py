import os

import pytest

PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_serial_esp',
]

serial_device_required = pytest.mark.skipif(os.getenv('DONT_SKIP_SERIAL_TESTS', False) is False,
                                            reason='after connected to espressif boards, '
                                                   'use "DONT_SKIP_SERIAL_TESTS" to run this tests')


@serial_device_required
def test_detect_port(testdir):
    testdir.makepyfile("""
        def test_detect_port(dut):
            assert dut.target
            assert dut.port
    """)

    result = testdir.runpytest(
        *PLUGINS,
    )

    result.assert_outcomes(passed=1)
