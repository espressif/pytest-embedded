import pytest  # noqa


def test_detect_port(testdir):
    testdir.makepyfile("""
        def test_detect_port(dut):
            dut[0].expect('Detecting chip type...')
            assert dut[0].serial.target == 'esp32s2'
            dut[1].expect('Detecting chip type...')
            assert dut[1].serial.target == 'esp32'
    """)

    result = testdir.runpytest(
        '--count', 2,
        '--embedded-services', 'esp',
        '--target', 'esp32s2|esp32'
    )

    result.assert_outcomes(passed=1)
