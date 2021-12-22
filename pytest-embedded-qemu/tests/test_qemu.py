import os

import pytest

qemu_bin_required = pytest.mark.skipif(os.getenv('DONT_SKIP_QEMU_TESTS', False) is False,
                                       reason='Build QEMU for ESP32 locally and then '
                                              'use "DONT_SKIP_QEMU_TESTS" to run this test.')


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
        '--embedded-services', 'idf,qemu',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
    )

    result.assert_outcomes(passed=1)


@qemu_bin_required
def test_multi_count_qemu(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_pexpect_by_qemu(dut):
            dut[0].expect('Hello world!')
            dut[1].expect('Restarting')
    """)

    result = testdir.runpytest(
        '--count', 2,
        '--embedded-services', 'idf,qemu|qemu',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}|',
        '--qemu-image-path', f'|{os.path.join(testdir.tmpdir, "esp32_qemu.bin")}',
        '--qemu-log-path', 'serial1.log|serial2.log',
    )

    result.assert_outcomes(passed=1)
