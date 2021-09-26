import os

import pytest  # noqa


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
        '--embedded-services', 'esp,idf',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=1)


def test_idf_app(testdir):
    testdir.makepyfile("""
        def test_idf_app(app, dut):
            import pytest

            assert len(app.flash_files) == 3
            assert app.target == 'esp32c3'

            with pytest.raises(AttributeError):
                assert getattr(dut, 'serial')
    """)

    result = testdir.runpytest(
        '--embedded-services', 'idf',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32c3'),
    )

    result.assert_outcomes(passed=1)


def test_multi_count_app(testdir):
    testdir.makepyfile("""
        def test_idf_app(app, dut):
            import pytest

            assert len(app[0].flash_files) == 3
            assert app[0].target == 'esp32'

            assert len(app[1].flash_files) == 3
            assert app[1].target == 'esp32c3'

            assert getattr(dut[0], 'serial')
            with pytest.raises(AttributeError):
                assert getattr(dut[1], 'serial')
    """)

    result = testdir.runpytest(
        '--count', 2,
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}'
                      f'|'
                      f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
        '--embedded-services', 'esp,idf|idf',
    )

    result.assert_outcomes(passed=1)
