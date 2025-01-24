import os


def test_arduino_serial_flash(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_arduino_app(app, dut):
            assert len(app.flash_files) == 3
            assert app.target == 'esp32'
            assert app.fqbn == 'espressif:esp32:esp32:PSRAM=enabled,PartitionScheme=huge_app'
            dut.expect('Hello Arduino!')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'arduino,esp',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_arduino'),
        '--build-dir',
        'build',
    )

    result.assert_outcomes(passed=1)
