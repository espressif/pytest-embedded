import os

PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_serial',
]


def test_serial_port(testdir):
    testdir.makepyfile("""
        import serial

        def test_serial_port(dut):
            assert type(dut.port_inst) == serial.Serial
    """)

    result = testdir.runpytest(
        *PLUGINS,
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world'),
    )

    result.assert_outcomes(passed=1)
