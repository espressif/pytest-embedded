import os
import shutil
import xml.etree.ElementTree as ET

import pytest

qemu_bin_required = pytest.mark.skipif(
    shutil.which('qemu-system-xtensa') is None,
    reason='Please make sure that `qemu-system-xtensa` is in your PATH env var. Build QEMU for ESP32 locally and then '
    'run `pytest` again',
)


@qemu_bin_required
def test_pexpect_write_efuse(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_pexpect_by_qemu(dut):
            dut.qemu.execute_efuse_command('burn-custom-mac 00:11:22:33:44:55')
            dut.expect('')

            with open('/tmp/test.test', 'rb') as f:
                content = f.read()

            expected_output = [
                '00000000:00000000000000000000000000800000',
                '00000010:00000000000010000000000000000000',
                '00000020:00000000000000000000000000000000',
                '00000030:00000000000000000000000000000000',
                '00000040:00000000000000000000000000000000',
                '00000050:000000000000000000000000b8001122',
                '00000060:33445500000000000000000000000000',
                '00000070:000000010000000000000000'
            ]

            lines = []
            for i in range(0, len(content), 16):
                line = content[i:i+16]
                hex_values = ''.join(f'{byte:02x}' for byte in line)
                lines.append(f'{i:08x}:{hex_values}')
            assert lines == expected_output

    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'idf,qemu',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--qemu-cli-args="-machine esp32 -nographic"',
        '--qemu-efuse-path',
        '/tmp/test.test',
    )

    result.assert_outcomes(passed=1)


@qemu_bin_required
def test_pexpect_by_qemu_xtensa(testdir):
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
        '--embedded-services',
        'idf,qemu',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
    )

    result.assert_outcomes(passed=1)


@qemu_bin_required
def test_pexpect_make_restart_by_qemu_xtensa(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_pexpect_by_qemu(dut):
            dut.expect('Hello world!')
            dut.hard_reset()
            dut.expect('cpu_start')
            dut.expect('Hello world!')
            dut.hard_reset()
            dut.expect('cpu_start')
            dut.expect('Hello world!')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'idf,qemu',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--qemu-cli-args="-machine esp32 -nographic"',
    )

    result.assert_outcomes(passed=1)


@qemu_bin_required
def test_pexpect_by_qemu_riscv(testdir):
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
        '--embedded-services',
        'idf,qemu',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32c3'),
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
        '--count',
        2,
        '--embedded-services',
        'idf,qemu|qemu',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}|',
        '--qemu-image-path',
        f'|{os.path.join(testdir.tmpdir, "esp32_qemu.bin")}',
    )

    result.assert_outcomes(passed=1)


@qemu_bin_required
def test_pre_flash_enc_qemu(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_pexpect_by_qemu(dut):
            dut.expect('Hello world!', timeout=120)
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    app_path = os.path.join(testdir.tmpdir, 'hello_world_esp32_flash_enc')
    keyfile_path = os.path.join(app_path, 'pre_encryption_key.bin')
    efuses_path = os.path.join(app_path, 'pre_encryption_efuses.bin')

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'idf,qemu',
        '--app-path',
        app_path,
        '--qemu-extra-args',
        f'-drive file={efuses_path},if=none,format=raw,id=efuse'
        ' -global driver=nvram.esp32.efuse,property=drive,value=efuse',
        '--encrypt',
        'true',
        '--keyfile',
        keyfile_path,
    )

    result.assert_outcomes(passed=1)


@qemu_bin_required
def test_qemu_use_idf_mixin_methods(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_qemu_use_idf_mixin_methods(dut):
            dut.run_all_single_board_cases()
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'idf,qemu',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "unit_test_app_esp32")}',
        '--junitxml',
        'report.xml',
    )

    result.assert_outcomes(failed=1)

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '1'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '2'
