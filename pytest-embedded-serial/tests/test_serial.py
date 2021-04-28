import os

PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_jtag',
    '-p', 'pytest_embedded_serial',
]


def test_pexpect(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_flash_serial(dut):
            dut.expect('Hello world!')
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        *PLUGINS,
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world'),
    )

    result.assert_outcomes(passed=1)
