def test_detect_port(testdir):
    testdir.makepyfile("""
        def test_detect_port(dut):
            assert dut[0].serial.target == 'esp32s2'
            assert dut[1].serial.target == 'esp32'
    """)

    result = testdir.runpytest(
        '-s',
        '--count', 2,
        '--embedded-services', 'esp',
        '--target', 'esp32s2|esp32')

    result.assert_outcomes(passed=1)
