import os

import pytest

qemu_bin_required = pytest.mark.skipif(
    os.getenv('DONT_SKIP_QEMU_TESTS', False) is False,
    reason='Build QEMU for ESP32 locally and then ' 'use "DONT_SKIP_QEMU_TESTS" to run this test.',
)


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
        '-s',
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
        '-s',
        '--count', 2,
        '--embedded-services', 'idf,qemu|qemu',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}|',
        '--qemu-image-path', f'|{os.path.join(testdir.tmpdir, "esp32_qemu.bin")}',
    )

    result.assert_outcomes(passed=1)


@qemu_bin_required
def test_secure_boot_and_pre_flash_encryption_qemu(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_pexpect_by_qemu(dut):
            dut.expect('Hello world!', timeout=600)
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    app_path = os.path.join(testdir.tmpdir, 'hello_world_esp32_sb_v2_and_fe')
    keyfile_path = os.path.join(app_path, 'pre_encryption_key.bin')
    efuses_path = os.path.join(app_path, 'sb_v2_and_fe_efuses.bin')

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'idf,qemu',
        '--app-path', app_path,
        '--qemu-extra-args',f'-drive file={efuses_path},if=none,format=raw,id=efuse'
        ' -global driver=nvram.esp32.efuse,property=drive,value=efuse',
        '--encrypt', 'true',
        '--keyfile', keyfile_path,
    )

    result.assert_outcomes(passed=1)
