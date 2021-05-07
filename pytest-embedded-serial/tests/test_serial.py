PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_serial',
]


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
