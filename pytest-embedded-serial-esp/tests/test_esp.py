import re


def test_detect_port(testdir):
    testdir.makepyfile(
        """
        def test_detect_port(dut):
            assert dut[0].serial.target == 'esp32c3'
            assert dut[1].serial.target == 'esp32'
    """
    )

    result = testdir.runpytest(
        '-s',
        '--count', 2,
        '--embedded-services', 'esp',
        '--target', 'esp32c3|esp32',
    )

    result.assert_outcomes(passed=1)


def test_detect_port_with_cache(testdir, caplog, first_index_of_messages):
    testdir.makepyfile(
        """
        def test_detect_port(dut):
            assert dut[0].serial.target == 'esp32c3'
            assert dut[1].serial.target == 'esp32'

        def test_detect_port_again(dut):
            assert dut[0].serial.target == 'esp32c3'
            assert dut[1].serial.target == 'esp32'
    """
    )

    result = testdir.runpytest(
        '-s',
        '--count', 2,
        '--embedded-services', 'esp',
        '--target', 'esp32c3|esp32',
        '--log-cli-level', 'DEBUG',
    )

    result.assert_outcomes(passed=2)

    esp32c3_set_cache_index = first_index_of_messages(
        re.compile('^set port-target cache: .+ - esp32c3$', re.MULTILINE), caplog.messages
    )
    esp32_set_cache_index = first_index_of_messages(
        re.compile('^set port-target cache: .+ - esp32$', re.MULTILINE), caplog.messages, esp32c3_set_cache_index + 1
    )
    esp32c3_hit_cache_index = first_index_of_messages(
        re.compile('^hit port-target cache: .+ - esp32c3$', re.MULTILINE), caplog.messages, esp32_set_cache_index + 1
    )
    first_index_of_messages(
        re.compile('^hit port-target cache: .+ - esp32$', re.MULTILINE), caplog.messages, esp32c3_hit_cache_index + 1
    )
