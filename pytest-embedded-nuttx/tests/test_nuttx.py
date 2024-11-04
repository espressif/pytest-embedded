import os


def test_nuttx_app_info(testdir):
    testdir.makepyfile("""
        import pytest

        def test_nuttx_app(app):
            assert 'esp32s3' == app.target
            assert '40m' == app.flash_freq
            assert '4MB' == app.flash_size
            assert 'dio' == app.flash_mode
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'nuttx,esp',
        '--target', 'esp32s3',
        '--app-path', os.path.join(testdir.tmpdir, "hello_world_nuttx")
    )

    result.assert_outcomes(passed=1)


def test_nuttx_app_mcuboot(testdir):
    testdir.makepyfile("""
        import pytest

        def test_nuttx_app_mcuboot(app):
            assert 'esp32s3' == app.target
            assert '40m' == app.flash_freq
            assert '4MB' == app.flash_size
            assert 'dio' == app.flash_mode
            assert None != app.bootloader_file
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'nuttx,esp',
        '--target', 'esp32s3',
        '--app-path', os.path.join(testdir.tmpdir, "hello_world_nuttx_mcuboot")
    )

    result.assert_outcomes(passed=1)
