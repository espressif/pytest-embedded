import os
import shutil

import pytest

espemu_bin_required = pytest.mark.skipif(
    shutil.which('esp-emu') is None,
    reason='Please make sure esp-emu is installed and on PATH. See https://github.com/espressif/esp-emulator#install',
)


@espemu_bin_required
def test_pexpect_by_espemu(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_pexpect_by_espemu(dut):
            dut.expect('Hello world!')
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'idf,espemu',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32c3'),
    )

    result.assert_outcomes(passed=1)


@espemu_bin_required
def test_multi_count_espemu(testdir):
    testdir.makepyfile("""
        def test_multi_count_espemu(dut):
            dut[0].expect('Hello world!')
            dut[1].expect('Restarting')
    """)

    result = testdir.runpytest(
        '-s',
        '--count',
        2,
        '--embedded-services',
        'idf,espemu|idf,espemu',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}|{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
    )

    result.assert_outcomes(passed=1)


@espemu_bin_required
def test_unsupported_target_espemu(testdir):
    testdir.makepyfile("""
        def test_unsupported_target_espemu(dut):
            pass
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'idf,espemu',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),  # xtensa, not emulated
    )

    result.assert_outcomes(errors=1)
