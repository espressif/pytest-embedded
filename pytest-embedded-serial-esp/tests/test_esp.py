PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_serial_esp',
]


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
