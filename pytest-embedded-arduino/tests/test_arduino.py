import os


def test_arduino_serial_flash(testdir):
    bin_path = os.path.join(testdir.tmpdir, 'hello_world_arduino', 'build', 'hello_world_arduino.ino.merged.bin')

    testdir.makepyfile(f"""
        import pexpect
        import pytest

        def test_arduino_app(app, dut):
            expected_bin = '{bin_path}'
            assert app.binary_file == expected_bin
            assert app.target == 'esp32'
            expected_fqbn = (
                "espressif:esp32:esp32:"
                "UploadSpeed=921600,"
                "CPUFreq=240,"
                "FlashFreq=80,"
                "FlashMode=qio,"
                "FlashSize=4M,"
                "PartitionScheme=huge_app,"
                "DebugLevel=none,"
                "PSRAM=enabled,"
                "LoopCore=1,"
                "EventsCore=1,"
                "EraseFlash=none,"
                "JTAGAdapter=default,"
                "ZigbeeMode=default"
            )
            assert app.fqbn == expected_fqbn
            dut.expect('Hello Arduino!')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'arduino,esp',
        '--build-dir',
        os.path.join(testdir.tmpdir, 'hello_world_arduino', 'build'),
    )

    result.assert_outcomes(passed=1)
