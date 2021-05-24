import os

import pytest

PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_idf',
    '-p', 'pytest_embedded_qemu_idf',
]

qemu_bin_required = pytest.mark.skipif(os.getenv('DONT_SKIP_QEMU_TESTS', False) is False,
                                       reason='after compiled qemu bin for esp32 locally, '
                                              'use "DONT_SKIP_QEMU_TESTS" to run this tests')


@qemu_bin_required
def test_pexpect_by_qemu(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_pexpect_by_qemu(dut):
            dut.expect('Hello world!')
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        *PLUGINS,
        # the current app is using esp32c3, which is not supported on qemu yet. Please specify to a esp32 one instead.
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world'),
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
        '--qemu-prog', 'qemu-system-xtensa'
    )

    result.assert_outcomes(passed=1)
