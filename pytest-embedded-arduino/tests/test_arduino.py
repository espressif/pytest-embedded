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


def test_fast_flash_saves_refs(testdir):
    """After the first flash, _flashed.bin references must be created."""
    testdir.makepyfile(r"""
        from pathlib import Path

        def test_refs_created(dut):
            dut.expect('Hello Arduino!')
            build = Path(dut.serial.app.binary_path)
            for _, binary in dut.serial.app.flash_files:
                p = Path(binary)
                ref = build / (p.stem + '_flashed' + p.suffix)
                assert ref.exists(), f'{ref.name} should exist after first flash'
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'arduino,esp',
        '--build-dir',
        os.path.join(testdir.tmpdir, 'hello_world_arduino', 'build'),
    )

    result.assert_outcomes(passed=1)


def test_fast_flash_reflash(testdir):
    """A second flash must succeed using --diff-with fast reflashing."""
    testdir.makepyfile(r"""
        def test_reflash(dut):
            dut.expect('Hello Arduino!')
            dut.serial.flash()
            dut.expect('Hello Arduino!')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'arduino,esp',
        '--build-dir',
        os.path.join(testdir.tmpdir, 'hello_world_arduino', 'build'),
    )

    result.assert_outcomes(passed=1)


def test_erase_flash_removes_refs(testdir):
    """erase_flash must delete all _flashed.bin references."""
    testdir.makepyfile(r"""
        from pathlib import Path

        def test_erase_refs(dut):
            dut.expect('Hello Arduino!')
            build = Path(dut.serial.app.binary_path)
            refs = [
                build / (Path(b).stem + '_flashed' + Path(b).suffix)
                for _, b in dut.serial.app.flash_files
            ]
            assert any(r.exists() for r in refs), 'refs should exist after first flash'

            dut.serial.erase_flash()
            for ref in refs:
                assert not ref.exists(), f'{ref.name} should be removed after erase'

            dut.serial.flash()
            dut.expect('Hello Arduino!')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'arduino,esp',
        '--build-dir',
        os.path.join(testdir.tmpdir, 'hello_world_arduino', 'build'),
    )

    result.assert_outcomes(passed=1)


def test_no_fast_flash_skips_refs(testdir):
    """--no-fast-flash must not create reference binaries."""
    testdir.makepyfile(r"""
        from pathlib import Path

        def test_no_refs(dut):
            dut.expect('Hello Arduino!')
            build = Path(dut.serial.app.binary_path)
            refs = [
                build / (Path(b).stem + '_flashed' + Path(b).suffix)
                for _, b in dut.serial.app.flash_files
            ]
            for ref in refs:
                assert not ref.exists(), f'{ref.name} should not exist with --no-fast-flash'
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'arduino,esp',
        '--build-dir',
        os.path.join(testdir.tmpdir, 'hello_world_arduino', 'build'),
        '--no-fast-flash',
        'y',
    )

    result.assert_outcomes(passed=1)
