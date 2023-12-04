import os
import platform
import re
import tempfile
import xml.etree.ElementTree as ET

import pytest
from pytest_embedded_idf.dut import IdfDut

toolchain_required = pytest.mark.skipif(
    os.getenv('PATH') is None or os.path.join('riscv32-esp-elf-gdb', 'bin') not in os.getenv('PATH'),
    reason="'riscv32-esp-elf-gdb' is not found in $PATH. The test execution will be skipped",
)


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
    )

    result.assert_outcomes(passed=1)


def test_idf_serial_flash_with_erase_nvs(testdir):
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
        '--erase-nvs', 'y',
    )

    result.assert_outcomes(passed=1)


def test_idf_serial_flash_with_erase_nvs_but_no_parttool(testdir, capsys, monkeypatch):
    monkeypatch.setenv('IDF_PATH', tempfile.tempdir)

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
        '--erase-nvs', 'y',
    )

    result.assert_outcomes(errors=1)
    assert 'Partition Tool not found' in capsys.readouterr().out


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


def test_multi_dut_app(testdir):
    testdir.makepyfile("""
        import pytest

        def test_multi_dut_app(app, dut):
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


def test_multi_dut_autoflash(testdir):
    testdir.makepyfile("""
        import pytest
        import pexpect

        def test_multi_dut_autoflash(app, dut):
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
        '--skip-autoflash', 'y|false',
        '--embedded-services', 'esp,idf',
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=1)


def test_cache_skip_autoflash(testdir, caplog, first_index_of_messages):
    testdir.makepyfile("""
        import pytest
        import pexpect

        def test_autoflash(app, dut):
            dut.expect('Hash of data verified.', timeout=5)

        def test_autoflash_again(app, dut):
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('Hash of data verified.', timeout=5)
    """)

    result = testdir.runpytest(
        '-s',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--embedded-services', 'esp,idf',
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
        '--log-cli-level', 'DEBUG',
    )

    result.assert_outcomes(passed=2)

    set_app_cache_i = first_index_of_messages(
        re.compile(r'^set port-app cache:.+hello_world_esp32[\\/]build$', re.MULTILINE),
        caplog.messages,
    )
    first_index_of_messages(
        re.compile(r'^hit port-app cache:.+hello_world_esp32[\\/]build$', re.MULTILINE),
        caplog.messages,
        set_app_cache_i + 1
    )


def test_cache_skip_autoflash_with_confirm(testdir, caplog, first_index_of_messages):
    testdir.makepyfile("""
        import pytest
        import pexpect

        def test_autoflash(app, dut):
            dut.expect('Hash of data verified.', timeout=5)

        def test_autoflash_again(app, dut):
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('Hash of data verified.', timeout=5)
    """)

    result = testdir.runpytest(
        '-s',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--embedded-services', 'esp,idf',
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
        '--log-cli-level', 'DEBUG',
        '--confirm-target-elf-sha256', 'y',
    )

    result.assert_outcomes(passed=2)

    set_app_cache_i = first_index_of_messages(
        re.compile(r'^set port-app cache:.+hello_world_esp32[\\/]build$', re.MULTILINE),
        caplog.messages,
    )
    hit_app_cache_i = first_index_of_messages(
        re.compile(r'^hit port-app cache:.+hello_world_esp32[\\/]build$', re.MULTILINE),
        caplog.messages,
        set_app_cache_i + 1
    )
    first_index_of_messages(
        re.compile(r'Confirmed target elf file sha256 the same as your local one\.$', re.MULTILINE),
        caplog.messages,
        hit_app_cache_i + 1,
    )


def test_different_build_dir(testdir):
    os.rename(os.path.join(testdir.tmpdir, 'hello_world_esp32', 'build'),
              os.path.join(testdir.tmpdir, 'hello_world_esp32', 'test_new_name'))

    testdir.makepyfile("""
        import pytest

        def test_multi_dut_app(app, dut):
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


def test_multi_dut_read_flash(testdir):
    testdir.makepyfile(r"""
        import pytest
        import pexpect

        def test_multi_dut_read_flash(app, serial, dut):
            dut[0].expect('Hash of data verified.', timeout=5)
            dut[0].expect_exact('Hello world!', timeout=5)

            dut[1].expect('Hash of data verified.', timeout=5)
            dut[1].expect_exact('Hello world!', timeout=5)

            serial[0].dump_flash(partition='phy_init', output='./test.bin')
            serial[1].dump_flash(partition='phy_init', output='./test.bin')

            dut[0].expect_exact('Hello world!', timeout=5)
            dut[1].expect_exact('Hello world!', timeout=5)
    """)

    result = testdir.runpytest(
        '-s',
        '--count', 2,
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}'
                      f'|'
                      f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
        '--embedded-services', 'esp,idf',
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=1)


def test_no_elf_file(testdir):
    testdir.makepyfile(r"""
         import pytest
         import pexpect

         def test_flash_with_no_elf_file(dut):
             dut.expect('Hash of data verified.', timeout=5)
             dut.expect_exact('Hello world!', timeout=5)
     """)

    os.remove(os.path.join(testdir.tmpdir, 'hello_world_esp32', 'build', 'hello_world.elf'))

    result = testdir.runpytest(
        '-s',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--embedded-services', 'esp,idf',
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=1)


def test_erase_all(testdir):
    testdir.makepyfile(r"""
        def test_detect_port(dut):
            for _ in range(3):
                dut.expect(r'Flash will be erased from 0x\d+ to 0x\d+')
            dut.expect('Hash of data verified.', timeout=5)
            dut.expect_exact('Hello world!', timeout=5)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--target', 'esp32',
        '--erase-all', 'y',
    )

    result.assert_outcomes(passed=1)


def test_erase_flash(testdir):
    testdir.makepyfile(r"""
        def test_detect_port(dut):
            dut.serial.erase_flash()
            dut.serial.flash()
            dut.expect('Hash of data verified.', timeout=5)
            dut.expect_exact('Hello world!', timeout=5)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--target', 'esp32',
    )

    result.assert_outcomes(passed=1)


@pytest.mark.skipif(platform.machine() != 'x86_64', reason='The test is intended to be run on an x86_64 machine.')
@pytest.mark.temp_disable_packages('pytest_embedded_serial')
def test_hello_world_linux(testdir):
    testdir.makepyfile(r"""
        import pytest

        def test_hello_world_linux(dut):
            with pytest.raises(ImportError):
                import pytest_embedded_serial

            dut.expect('Hello world!')
            dut.expect('Restarting')
    """)
    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'idf',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_linux")}',
        '--target', 'linux',
    )

    result.assert_outcomes(passed=1)


@toolchain_required
def test_check_coredump(testdir, caplog, first_index_of_messages):
    testdir.makepyfile(r"""
        import pexpect
        import pytest

        def test_check_coredump(dut):
            dut.expect(pexpect.TIMEOUT, timeout=10)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3_panic")}',
        '--target', 'esp32c3',
        '--panic-output-decode-script', os.path.join(testdir.tmpdir, 'gdb_panic_server.py'),
        '--log-cli-level', 'INFO',
    )
    first_index_of_messages(
        re.compile(r'app_main \(\) at /COMPONENT_MAIN_DIR/hello_world_main.c:17', re.MULTILINE),
        caplog.messages,
    )

    result.assert_outcomes(passed=1)


@toolchain_required
def test_skip_check_coredump(testdir, caplog, first_index_of_messages):
    testdir.makepyfile(r"""
        import pexpect
        import pytest

        def test_skip_check_coredump(dut):
            dut.expect(pexpect.TIMEOUT, timeout=5)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3_panic")}',
        '--panic-output-decode-script', os.path.join(testdir.tmpdir, 'gdb_panic_server.py'),
        '--skip-check-coredump', 'True',
        '--log-cli-level', 'INFO',
    )
    with pytest.raises(AssertionError):
        first_index_of_messages(
            re.compile(r'app_main \(\) at /COMPONENT_MAIN_DIR/hello_world_main.c:17', re.MULTILINE),
            caplog.messages,
        )

    result.assert_outcomes(passed=1)


def test_idf_parse_test_menu():
    s = '''(1)\t"adc1 and i2s work with wifi" [adc][ignore]
(2)\t"I2C master write slave test" [i2c][test_env=UT_T2_I2C][timeout=150][multi_device]
\t(1)\t"i2c_master_write_test"
\t(2)\t"i2c_slave_read_test"
(3)\t"LEDC continue work after software reset" [ledc][multi_stage]
\t(1)\t"ledc_cpu_reset_test_first_stage"
\t(2)\t"ledc_cpu_reset_test_second_stage"
'''
    test_menu = IdfDut._parse_unity_menu_from_str(s)

    assert len(test_menu) == 3

    assert test_menu[0].name == 'adc1 and i2s work with wifi'
    assert test_menu[0].groups[0] == 'adc'
    assert test_menu[0].keywords[0] == 'ignore'

    assert test_menu[1].name == 'I2C master write slave test'
    assert test_menu[1].groups[0] == 'i2c'
    assert test_menu[1].type == 'multi_device'
    assert test_menu[1].attributes['test_env'] == 'UT_T2_I2C'
    assert test_menu[1].attributes['timeout'] == '150'
    assert test_menu[1].subcases[0]['index'] == 1
    assert test_menu[1].subcases[0]['name'] == 'i2c_master_write_test'
    assert test_menu[1].subcases[1]['index'] == 2
    assert test_menu[1].subcases[1]['name'] == 'i2c_slave_read_test'

    assert test_menu[2].name == 'LEDC continue work after software reset'
    assert test_menu[2].groups[0] == 'ledc'
    assert test_menu[2].type == 'multi_stage'
    assert test_menu[2].subcases[0]['index'] == 1
    assert test_menu[2].subcases[0]['name'] == 'ledc_cpu_reset_test_first_stage'
    assert test_menu[2].subcases[1]['index'] == 2
    assert test_menu[2].subcases[1]['name'] == 'ledc_cpu_reset_test_second_stage'


def test_idf_multi_hard_reset_and_expect(testdir):
    testdir.makepyfile(r"""
        def test_idf_hard_reset_and_expect(dut):
            for _ in range(10):
                dut.serial.hard_reset()
                dut.expect_exact('Hello world!')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--log-cli-level', 'DEBUG',
    )

    result.assert_outcomes(passed=1)


def test_dut_run_all_single_board_cases(testdir):
    testdir.makepyfile(r"""
        def test_dut_run_all_single_board_cases(dut):
            dut.run_all_single_board_cases(timeout=10)
    """)
    testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf',
        '--app-path', os.path.join(testdir.tmpdir, 'unit_test_app_esp32c3'),
        '--log-cli-level', 'DEBUG',
        '--junitxml', 'report.xml',
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '1'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '2'

    testcases = junit_report.findall('.//testcase')
    succeed = testcases[0]
    failed = testcases[1]
    multi_stage = testcases[2]

    assert succeed.attrib['name'] == 'normal_case1'

    assert failed.attrib['name'] == 'normal_case2'
    assert 10 < float(failed.attrib['time']) < 10.1
    assert failed[0].attrib['message']

    assert multi_stage.attrib['name'] == 'multiple_stages_test'


def test_unity_test_case_runner(testdir):
    testdir.makepyfile(r"""
        def test_unity_test_case_runner(unity_tester):
            unity_tester.run_all_cases()
    """)

    testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf',
        '--count', 2,
        '--app-path', f'{os.path.join(testdir.tmpdir, "unit_test_app_esp32")}'
                      f'|'
                      f'{os.path.join(testdir.tmpdir, "unit_test_app_esp32c3")}',
        '--log-cli-level', 'DEBUG',
        '--junitxml', 'report.xml'
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '1'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '3'

    assert junit_report[0].get('name') == 'normal_case1'
    assert junit_report[0].find('failure') is None
    assert junit_report[1].get('name') == 'normal_case2'
    assert junit_report[1].find('failure') is not None
    assert junit_report[2].get('name') == 'multiple_stages_test'
    assert junit_report[2].find('failure') is None
    assert junit_report[3].get('name') == 'multiple_devices_test'
    assert junit_report[3].find('failure') is None


def test_erase_all_with_port_cache(testdir):
    testdir.makepyfile(r"""
        def test_erase_all_with_port_cache_case1(dut):
            dut.expect('Hash of data verified.', timeout=5)
            dut.expect_exact('Hello world!', timeout=5)

        def test_erase_all_with_port_cache_case2(dut):
            dut.expect('Hash of data verified.', timeout=5)
            dut.expect_exact('Hello world!', timeout=5)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf',
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--target', 'esp32',
        '--erase-all', 'y',
    )

    result.assert_outcomes(passed=2)
