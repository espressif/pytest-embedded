import os


def test_idf_serial_flash(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_idf_serial_flash(dut):
            dut.expect('Hash of data verified.')  # from flash
            dut.expect('Hello world!')
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=1)


def test_idf_app(testdir):
    testdir.makepyfile("""
        import pytest

        def test_idf_app(app, dut):
            assert len(app.flash_files) == 3
            assert app.target == 'esp32c3'

            with pytest.raises(AttributeError):
                assert getattr(dut, 'serial')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'idf',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32c3'),
    )

    result.assert_outcomes(passed=1)


def test_multi_count_app(testdir):
    testdir.makepyfile("""
        import pytest

        def test_multi_count_app(app, dut):
            assert len(app[0].flash_files) == 3
            assert app[0].target == 'esp32'

            assert len(app[1].flash_files) == 3
            assert app[1].target == 'esp32c3'

            assert getattr(dut[0], 'serial')
            with pytest.raises(AttributeError):
                assert getattr(dut[1], 'serial')
    """)

    result = testdir.runpytest(
        '-s',
        '--count', 2,
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}'
                      f'|'
                      f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
        '--embedded-services', 'esp,idf|idf',
    )

    result.assert_outcomes(passed=1)


def test_multi_count_autoflash(testdir):
    testdir.makepyfile("""
        import pytest
        import pexpect

        def test_multi_count_autoflash(app, dut):
            skip_dut = dut[0]
            auto_dut = dut[1]
            with pytest.raises(pexpect.TIMEOUT):
                skip_dut.expect('Hash of data verified.', timeout=5)
            auto_dut.expect('Hash of data verified.', timeout=5)
    """)

    result = testdir.runpytest(
        '-s',
        '--count', 2,
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}'
                      f'|'
                      f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
        '--skip-autoflash', 'true|false',
        '--embedded-services', 'esp,idf',
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=1)


def test_different_build_dir(testdir):
    os.rename(os.path.join(testdir.tmpdir, 'hello_world_esp32', 'build'),
              os.path.join(testdir.tmpdir, 'hello_world_esp32', 'test_new_name'))

    testdir.makepyfile("""
        import pytest

        def test_multi_count_app(app, dut):
            assert app.target == 'esp32'
            assert app.binary_path.endswith('test_new_name')
    """)

    result = testdir.runpytest(
        '-s',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--build-dir', 'test_new_name',
        '--embedded-services', 'idf',
    )

    result.assert_outcomes(passed=1)

    result = testdir.runpytest(
        '-s',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--build-dir', os.path.join(testdir.tmpdir, 'hello_world_esp32', 'test_new_name'),
        '--embedded-services', 'idf',
    )

    result.assert_outcomes(passed=1)
