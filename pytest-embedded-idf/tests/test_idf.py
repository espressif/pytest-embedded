import os

import pytest

PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_serial_esp',
    '-p', 'pytest_embedded_idf',
]

PLUGINS_WITHOUT_SERIAL = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_idf',
]

serial_device_required = pytest.mark.skipif(os.getenv('DONT_SKIP_SERIAL_TESTS', False) is False,
                                            reason='after connected to espressif boards, '
                                                   'use "DONT_SKIP_SERIAL_TESTS" to run this test')


@serial_device_required
def test_pexpect(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_idf_serial_flash(dut):
            dut.expect('(100 %)')  # from flash
            dut.expect('Hello world!')
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        *PLUGINS,
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
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
        *PLUGINS_WITHOUT_SERIAL,
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32c3'),
    )

    result.assert_outcomes(passed=1)
