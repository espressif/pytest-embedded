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
            assert dut.serial.esp_flash_force == False
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
    )

    result.assert_outcomes(passed=1)


def test_esp_flash_force_flag(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_idf_serial_flash(dut):
            dut.expect('Hello world!')
            assert dut.serial.esp_flash_force == True
    """)
    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--esp-flash-force',
    )

    result.assert_outcomes(passed=1)


def test_custom_idf_device_dut(testdir):
    p = os.path.join(testdir.tmpdir, 'hello_world_esp32')
    p_c3 = os.path.join(testdir.tmpdir, 'hello_world_esp32c3')
    unity_test_path = os.path.join(testdir.tmpdir, 'unit_test_app_esp32')
    unity_test_path_c3 = os.path.join(testdir.tmpdir, 'unit_test_app_esp32c3')
    testdir.makepyfile(f"""
        import pytest

        def test_idf_custom_dev():
            from pytest_embedded.dut_factory import DutFactory
            dut = DutFactory.create(embedded_services='esp,idf', app_path=r'{p}')
            dut.expect("Hello")

        def test_idf_mixed(dut):
            from pytest_embedded.dut_factory import DutFactory
            dut_c3 = DutFactory.create(embedded_services='esp,idf', app_path=r'{p_c3}')
            dut_c3.expect("Hello")
            dut.expect("Hello")
            assert dut_c3.serial.port!=dut.serial.port

        def test_idf_unity_tester():
            from pytest_embedded.dut_factory import DutFactory
            dut1 = DutFactory.create(embedded_services='esp,idf', app_path=r'{unity_test_path}')
            dut2 = DutFactory.create(embedded_services='esp,idf', app_path=r'{unity_test_path_c3}')
            tester = DutFactory.unity_tester(dut1, dut2)
            tester.run_all_multi_dev_cases(timeout=10)

        def test_idf_run_all_single_board_cases():
            from pytest_embedded.dut_factory import DutFactory
            dut1 = DutFactory.create(embedded_services='esp,idf', app_path=r'{unity_test_path}')
            dut1.run_all_single_board_cases(reset=True, timeout=10)
    """)

    result = testdir.runpytest(
        '-s',
        '--app-path',
        p,
        '--embedded-services',
        'esp,idf',
        '--junitxml',
        'report.xml',
    )
    result.assert_outcomes(passed=4, errors=0)  # FIXME, dut-factory mode can't raise error now

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '2'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '6'


def test_idf_serial_flash_with_erase_nvs(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_idf_serial_flash_with_erase_nvs(dut):
            dut.expect('region')  # from "erase-nvs"
            dut.expect('Hash of data verified.')  # from flash
            dut.expect('Hello world!')
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--part-tool',
        os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
        '--erase-nvs',
        'y',
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
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--erase-nvs',
        'y',
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
        '--embedded-services',
        'idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32c3'),
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
        '--count',
        2,
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}|{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
        '--embedded-services',
        'esp,idf|idf',
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
        '--count',
        2,
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}|{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
        '--skip-autoflash',
        'y|false',
        '--embedded-services',
        'esp,idf',
        '--part-tool',
        os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
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
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--embedded-services',
        'esp,idf',
        '--part-tool',
        os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
        '--log-cli-level',
        'DEBUG',
    )

    result.assert_outcomes(passed=2)

    set_app_cache_i = first_index_of_messages(
        re.compile(r'^set port-app cache:.+hello_world_esp32[\\/]build$', re.MULTILINE),
        caplog.messages,
    )
    first_index_of_messages(
        re.compile(r'^hit port-app cache:.+hello_world_esp32[\\/]build$', re.MULTILINE),
        caplog.messages,
        set_app_cache_i + 1,
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
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--embedded-services',
        'esp,idf',
        '--part-tool',
        os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
        '--log-cli-level',
        'DEBUG',
        '--confirm-target-elf-sha256',
        'y',
    )

    result.assert_outcomes(passed=2)

    set_app_cache_i = first_index_of_messages(
        re.compile(r'^set port-app cache:.+hello_world_esp32[\\/]build$', re.MULTILINE),
        caplog.messages,
    )
    hit_app_cache_i = first_index_of_messages(
        re.compile(r'^hit port-app cache:.+hello_world_esp32[\\/]build$', re.MULTILINE),
        caplog.messages,
        set_app_cache_i + 1,
    )
    first_index_of_messages(
        re.compile(r'Confirmed target elf file sha256 the same as your local one\.$', re.MULTILINE),
        caplog.messages,
        hit_app_cache_i + 1,
    )


def test_different_build_dir(testdir):
    os.rename(
        os.path.join(testdir.tmpdir, 'hello_world_esp32', 'build'),
        os.path.join(testdir.tmpdir, 'hello_world_esp32', 'test_new_name'),
    )

    testdir.makepyfile("""
        import pytest

        def test_multi_dut_app(app, dut):
            assert app.target == 'esp32'
            assert app.binary_path.endswith('test_new_name')
    """)

    result = testdir.runpytest(
        '-s',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--build-dir',
        'test_new_name',
        '--embedded-services',
        'idf',
    )

    result.assert_outcomes(passed=1)

    result = testdir.runpytest(
        '-s',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--build-dir',
        os.path.join(testdir.tmpdir, 'hello_world_esp32', 'test_new_name'),
        '--embedded-services',
        'idf',
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
        '--count',
        2,
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}|{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
        '--embedded-services',
        'esp,idf',
        '--part-tool',
        os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=1)


def test_flash_another_app(testdir):
    testdir.makepyfile(
        r"""
        import pytest
        import pexpect

        from pytest_embedded_idf import IdfApp

        def test_flash_another_app(dut):
            dut.serial.flash(IdfApp('{}'))
            dut.expect('Hash of data verified.', timeout=5)
            dut.expect_exact('Hello world!', timeout=5)
    """.format(os.path.join(testdir.tmpdir, 'hello_world_esp32'))
    )

    result = testdir.runpytest(
        '-s',
        '--app-path',
        os.path.join(testdir.tmpdir, 'unit_test_app_esp32'),
        '--embedded-services',
        'esp,idf',
        '--part-tool',
        os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=1)


def test_flash_with_no_elf_file(testdir):
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
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--embedded-services',
        'esp,idf',
        '--part-tool',
        os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
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
        '--embedded-services',
        'esp,idf',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--target',
        'esp32',
        '--erase-all',
        'y',
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
        '--embedded-services',
        'esp,idf',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--target',
        'esp32',
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
        '--embedded-services',
        'idf',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_linux")}',
        '--target',
        'linux',
    )

    result.assert_outcomes(passed=1)


@pytest.mark.skipif(platform.machine() != 'x86_64', reason='The test is intended to be run on an x86_64 machine.')
def test_unity_tester_with_linux(testdir):
    testdir.makepyfile(r"""

    def test_unity_tester_with_linux(dut):
        dut.run_all_single_board_cases()
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'idf',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "unit_test_app_linux")}',
        '--target',
        'linux',
        '--junitxml',
        'report.xml',
    )

    result.assert_outcomes(passed=1)

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '0'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '46'


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
        '--embedded-services',
        'esp,idf',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3_panic")}',
        '--target',
        'esp32c3',
        '--panic-output-decode-script',
        os.path.join(testdir.tmpdir, 'gdb_panic_server.py'),
        '--log-cli-level',
        'INFO',
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
        '--embedded-services',
        'esp,idf',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3_panic")}',
        '--panic-output-decode-script',
        os.path.join(testdir.tmpdir, 'gdb_panic_server.py'),
        '--skip-check-coredump',
        'True',
        '--log-cli-level',
        'INFO',
    )
    with pytest.raises(AssertionError):
        first_index_of_messages(
            re.compile(r'app_main \(\) at /COMPONENT_MAIN_DIR/hello_world_main.c:17', re.MULTILINE),
            caplog.messages,
        )

    result.assert_outcomes(passed=1)


def test_idf_parse_test_menu():
    s = """(1)\t"adc1 and i2s work with wifi" [adc][ignore]
(2)\t"I2C master write slave test" [i2c][test_env=UT_T2_I2C][timeout=150][multi_device]
\t(1)\t"i2c_master_write_test"
\t(2)\t"i2c_slave_read_test"
(3)\t"LEDC continue work after software reset" [ledc][multi_stage]
\t(1)\t"ledc_cpu_reset_test_first_stage"
\t(2)\t"ledc_cpu_reset_test_second_stage"
"""
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
        '--embedded-services',
        'esp,idf',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--log-cli-level',
        'DEBUG',
    )

    result.assert_outcomes(passed=1)


def test_select_to_run():
    from pytest_embedded_idf.unity_tester import IdfUnityDutMixin

    assert IdfUnityDutMixin._select_to_run(None, None, None, None, None, None)

    assert IdfUnityDutMixin._select_to_run(None, ['name_hello', 'name_world'], None, None, 'name_hello', None)

    assert not IdfUnityDutMixin._select_to_run(None, ['name_hello', 'name_world'], None, None, 'name_hel', None)

    assert IdfUnityDutMixin._select_to_run(None, None, {'red': 255}, None, None, {'red': 255, 'green': 10, 'blue': 33})

    assert not IdfUnityDutMixin._select_to_run(
        None, None, {'red': 25}, None, None, {'red': 255, 'green': 10, 'blue': 33}
    )

    assert IdfUnityDutMixin._select_to_run(
        None, None, {'red': 255, 'green': 10}, None, None, {'red': 255, 'green': 10, 'blue': 33}
    )

    assert not IdfUnityDutMixin._select_to_run(
        None, None, {'red': 255, 'green': 0}, None, None, {'red': 255, 'green': 10, 'blue': 33}
    )

    assert IdfUnityDutMixin._select_to_run([['hello']], None, None, ['hello', 'world'], None, None)

    assert not IdfUnityDutMixin._select_to_run([['!hello']], None, None, ['hello', 'world'], None, None)

    assert not IdfUnityDutMixin._select_to_run([['hello', '!world']], None, None, ['hello', 'world'], None, None)

    assert IdfUnityDutMixin._select_to_run(
        [['hello', '!world'], ['sun']], None, None, ['hello', 'world', 'sun'], None, None
    )

    assert IdfUnityDutMixin._select_to_run([['hello', '!w']], None, None, ['hello', 'world'], None, None)


def test_dut_run_all_single_board_cases_reset_false(testdir):
    testdir.makepyfile(r"""
        def test_dut_run_all_single_board_cases(dut):
            dut.run_all_single_board_cases(timeout=10)
    """)
    testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'unit_test_app_esp32c3'),
        '--log-cli-level',
        'DEBUG',
        '--junitxml',
        'report.xml',
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '2'
    assert junit_report.attrib['skipped'] == '2'
    assert junit_report.attrib['tests'] == '1'

    testcases = junit_report.findall('.//testcase')
    assert testcases[0].attrib['name'] == 'normal_case_pass'
    assert testcases[1].attrib['name'] == 'normal_case_crash'
    assert testcases[2].attrib['name'] == 'normal_case_stuck'
    assert testcases[3].attrib['name'] == 'normal_case_skip_when_not_reset'
    assert testcases[4].attrib['name'] == 'multiple_stages_test'

    assert 10 < float(testcases[1].attrib['time']) < 10.1
    assert 'Guru Meditation Error' in testcases[1][0].attrib['message']

    assert 'Skipped due to a failure before test execution.' in testcases[3][0].attrib['message']
    assert 'Skipped due to a failure before test execution.' in testcases[4][0].attrib['message']


def test_dut_run_all_single_board_cases_reset_true(testdir):
    testdir.makepyfile(r"""
        def test_dut_run_all_single_board_cases(dut):
            dut.run_all_single_board_cases(reset=True, timeout=10)
    """)
    testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'unit_test_app_esp32'),
        '--log-cli-level',
        'DEBUG',
        '--junitxml',
        'report.xml',
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '2'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '3'

    testcases = junit_report.findall('.//testcase')
    assert testcases[0].attrib['name'] == 'normal_case_pass'
    assert testcases[1].attrib['name'] == 'normal_case_crash'
    assert testcases[2].attrib['name'] == 'normal_case_stuck'
    assert testcases[3].attrib['name'] == 'normal_case_skip_when_not_reset'
    assert testcases[4].attrib['name'] == 'multiple_stages_test'

    assert 10 < float(testcases[1].attrib['time']) < 10.1
    assert 'Guru Meditation Error' in testcases[1][0].attrib['message']
    assert 'normal case stuck: infinite loop' in testcases[2][0].attrib['message']


def test_dut_run_all_single_board_cases_group(testdir):
    testdir.makepyfile(r"""
        def test_dut_run_all_single_board_cases(dut):
            dut.run_all_single_board_cases(group="normal_case", timeout=10)
    """)
    testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'unit_test_app_esp32'),
        '--log-cli-level',
        'DEBUG',
        '--junitxml',
        'report.xml',
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '2'
    assert junit_report.attrib['skipped'] == '1'
    assert junit_report.attrib['tests'] == '1'


def test_dut_run_all_single_board_cases_invert_group(testdir):
    testdir.makepyfile(r"""
        def test_dut_run_all_single_board_cases(dut):
            dut.run_all_single_board_cases(group="!normal_case", timeout=10)
    """)
    testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'unit_test_app_esp32'),
        '--junitxml',
        'report.xml',
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '0'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '1'


def test_dut_run_all_single_board_cases_by_names(testdir):
    testdir.makepyfile(r"""
        def test_dut_run_all_single_board_cases(dut):
            dut.run_all_single_board_cases(
                name=["normal_case_pass", "multiple_stages_test"]
            )
    """)
    testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'unit_test_app_esp32'),
        '--junitxml',
        'report.xml',
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '0'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '2'

    for testcase in junit_report.findall('testcase'):
        assert testcase.attrib['is_unity_case'] == '1'


def test_unity_test_case_runner_without_reset(testdir):
    testdir.makepyfile(r"""
        def test_unity_test_case_runner_without_reset(unity_tester):
            pass_case = unity_tester.test_menu[0]
            stuck_case = unity_tester.test_menu[2]
            multi_dev_case = unity_tester.test_menu[-1]
            unity_tester.run_normal_case(pass_case, timeout=5)
            unity_tester.run_normal_case(stuck_case, timeout=5)
            unity_tester.run_multi_dev_case(multi_dev_case, timeout=5)
    """)

    testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--count',
        2,
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "unit_test_app_esp32")}'
        f'|'
        f'{os.path.join(testdir.tmpdir, "unit_test_app_esp32c3")}',
        '--junitxml',
        'report.xml',
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '1'
    assert junit_report.attrib['skipped'] == '1'
    assert junit_report.attrib['tests'] == '1'


def test_unity_test_case_runner_with_reset(testdir):
    testdir.makepyfile(r"""
        def test_unity_test_case_runner_without_reset(unity_tester):
            pass_case = unity_tester.test_menu[0]
            stuck_case = unity_tester.test_menu[2]
            multi_dev_case = unity_tester.test_menu[-1]
            unity_tester.run_normal_case(pass_case, timeout=5)
            unity_tester.run_normal_case(stuck_case, timeout=5)
            unity_tester.run_multi_dev_case(multi_dev_case, reset=True, timeout=5)
    """)

    testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--count',
        2,
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "unit_test_app_esp32")}'
        f'|'
        f'{os.path.join(testdir.tmpdir, "unit_test_app_esp32c3")}',
        '--junitxml',
        'report.xml',
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '1'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '2'


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
        '--embedded-services',
        'esp,idf',
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}',
        '--target',
        'esp32',
        '--erase-all',
        'y',
    )

    result.assert_outcomes(passed=2)


def test_preserve_python_tests_with_failures(testdir):
    testdir.makepyfile(r"""
        def test_python_case(dut):
            dut.run_all_single_board_cases(
                name=["normal_case_pass", "normal_case_crash", "multiple_stages_test"]
            )
    """)

    testdir.runpytest(
        '-s',
        '--embedded-services',
        'esp,idf',
        '--app-path',
        os.path.join(testdir.tmpdir, 'unit_test_app_esp32c3'),
        '--junitxml',
        'report.xml',
        '--unity-test-report-mode',
        'merge',
    )

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '1'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '2'

    assert junit_report[0].attrib['is_unity_case'] == '0'  # Python test case
    for testcase in junit_report[1:]:
        assert testcase.attrib['is_unity_case'] == '1'
    assert junit_report[2].attrib['name'] == 'normal_case_crash'
    assert junit_report[2].find('failure') is not None


def test_esp_bool_parser_returned_values(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from esp_bool_parser import SOC_HEADERS, SUPPORTED_TARGETS

    assert SOC_HEADERS == {
        'esp32': {'SOC_A': 0, 'SOC_B': 1, 'SOC_C': 0},
        'esp32s2': {'SOC_A': 0, 'SOC_B': 0, 'SOC_C': 0},
        'esp32c3': {'SOC_A': 1, 'SOC_B': 1, 'SOC_C': 1},
        'esp32s3': {'SOC_A': 1, 'SOC_B': 0, 'SOC_C': 1},
        'esp32c2': {'SOC_A': 0, 'SOC_B': 1, 'SOC_C': 0},
        'esp32c6': {'SOC_A': 1, 'SOC_B': 0, 'SOC_C': 0},
        'esp32h2': {'SOC_A': 0, 'SOC_B': 1, 'SOC_C': 1},
        'esp32p4': {'SOC_A': 0, 'SOC_B': 0, 'SOC_C': 1},
        'linux': {},
        'esp32c5': {'SOC_A': 1, 'SOC_B': 1, 'SOC_C': 0},
        'esp32c61': {'SOC_A': 0, 'SOC_B': 0, 'SOC_C': 1},
        'esp32h21': {'SOC_A': 0, 'SOC_B': 0, 'SOC_C': 0},
    }
    assert SUPPORTED_TARGETS == ['esp32', 'esp32s2', 'esp32c3', 'esp32s3', 'esp32c2', 'esp32c6', 'esp32h2', 'esp32p4']


def test_skip_if_soc(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from esp_bool_parser import SOC_HEADERS, SUPPORTED_TARGETS

    def run_test_for_condition(condition, condition_func):
        to_skip = sum([1 for t in SUPPORTED_TARGETS if condition_func(SOC_HEADERS[t])])
        to_pass = len(SUPPORTED_TARGETS) - to_skip
        testdir.makepyfile(f"""
            import pytest
            from esp_bool_parser.constants import SUPPORTED_TARGETS

            @pytest.mark.skip_if_soc("{condition}")
            @pytest.mark.parametrize('target', SUPPORTED_TARGETS, indirect=True)
            def test_skip_if_for_condition():
                pass
        """)

        result = testdir.runpytest('-s', '--embedded-services', 'esp,idf')
        result.assert_outcomes(passed=to_pass, skipped=to_skip)

    for c, cf in [
        ('SOC_A == 1', lambda h: h['SOC_A'] == 1),
        ('SOC_A == 1 or SOC_B == 1', lambda h: h['SOC_A'] == 1 or h['SOC_B'] == 1),
        ('SOC_A == 1 and SOC_B == 1', lambda h: h['SOC_A'] == 1 and h['SOC_B'] == 1),
        ('SOC_A == 1 or SOC_B == 1 and SOC_C == 1', lambda h: h['SOC_A'] == 1 or (h['SOC_B'] == 1 and h['SOC_C'] == 1)),
        (
            'SOC_A == 1 and SOC_B == 0 or SOC_C == 1 ',
            lambda h: (h['SOC_A'] == 1 and h['SOC_B'] == 0) or h['SOC_C'] == 1,
        ),
    ]:
        run_test_for_condition(c, cf)


def test_soc_filtered_targets(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from pytest_embedded_idf.utils import soc_filtered_targets

    assert soc_filtered_targets('SOC_A == 1') == ['esp32c3', 'esp32s3', 'esp32c6', 'esp32c5']
    assert soc_filtered_targets('SOC_A == 1 or SOC_B == 1') == [
        'esp32',
        'esp32c3',
        'esp32s3',
        'esp32c2',
        'esp32c6',
        'esp32h2',
        'esp32c5',
    ]
    assert soc_filtered_targets('SOC_A == 1', 'all') == ['esp32c3', 'esp32s3', 'esp32c6', 'esp32c5']
    assert soc_filtered_targets('SOC_A == 1', targets='supported_targets') == ['esp32c3', 'esp32s3', 'esp32c6']
    assert soc_filtered_targets('SOC_A == 1', targets='preview_targets') == ['esp32c5']


def test_skip_if_soc_target_in_args(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv('IDF_PATH', str(testdir))

    def run_pytest_with_target(target):
        count = len(target.split('|'))
        return testdir.runpytest('--embedded-services', 'esp,idf', '--target', target, '--count', count)

    testdir.makepyfile("""
        import pytest

        @pytest.mark.skip_if_soc("SOC_A == 1")
        def test_from_args():
            pass

    """)

    results = [
        (run_pytest_with_target('auto'), {'passed': 1, 'failed': 0, 'skipped': 0}),
        (run_pytest_with_target('esp32|esp32'), {'passed': 1, 'failed': 0, 'skipped': 0}),
    ]

    for result, expected in results:
        result.assert_outcomes(**expected)


def test_expand_target_values_supported_targets(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv('IDF_PATH', str(testdir))

    from esp_bool_parser import SUPPORTED_TARGETS
    from pytest_embedded_idf.utils import _expand_target_values

    values = [['param_1', 'supported_targets', 'param_2']]
    result = _expand_target_values(values, 1)
    assert len(result) == len(SUPPORTED_TARGETS)
    for target, expanded in zip(SUPPORTED_TARGETS, result):
        assert expanded == ['param_1', target, 'param_2']


def test_expand_target_values_preview_targets(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv('IDF_PATH', str(testdir))

    from esp_bool_parser import PREVIEW_TARGETS
    from pytest_embedded_idf.utils import _expand_target_values

    """Test expansion of preview_targets"""
    values = [['param_1', 'preview_targets', 'param_2']]
    result = _expand_target_values(values, 1)

    assert len(result) == len(PREVIEW_TARGETS)
    for target, expanded in zip(PREVIEW_TARGETS, result):
        assert expanded == ['param_1', target, 'param_2']


def test_expand_target_values_specific_target(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv('IDF_PATH', str(testdir))

    from esp_bool_parser import SUPPORTED_TARGETS
    from pytest_embedded_idf.utils import _expand_target_values

    """Test handling of specific target"""
    values = [['param_1', 'esp32', 'param_2'], ['param_3', 'supported_targets', 'param_4']]
    result = _expand_target_values(values, 1)

    assert len(result) == 1 + len(SUPPORTED_TARGETS)
    assert result == [['param_1', 'esp32', 'param_2']] + [['param_3', _t, 'param_4'] for _t in SUPPORTED_TARGETS]


def test_process_pytest_value_simple(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    """Test processing of simple parameter values"""
    monkeypatch.setenv('IDF_PATH', str(testdir))

    from pytest_embedded_idf.utils import _process_pytest_value

    value = 'simple_value'
    result = _process_pytest_value(value, -1)
    assert result == 'simple_value'


def test_process_pytest_value_with_single_mark(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    """Test processing value with a single pytest mark"""
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from pytest_embedded_idf.utils import _process_pytest_value

    mark = pytest.mark.skip(reason='test')
    value = ['param1', 'param2', (mark,)]
    result = _process_pytest_value(value, 2)

    assert result == pytest.param(*('param1', 'param2'), marks=(mark))
    assert result.marks == (mark,)
    assert result.values == ('param1', 'param2')


def test_process_pytest_value_with_multiple_marks(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    """Test processing value with multiple pytest marks"""
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from pytest_embedded_idf.utils import _process_pytest_value

    marks = (pytest.mark.skip(reason='test'), pytest.mark.xfail())
    value = ['param1', 'param2', marks]
    result = _process_pytest_value(value, 2)

    assert result == pytest.param(*('param1', 'param2'), marks=marks)
    assert result.marks == marks
    assert result.values == ('param1', 'param2')


def test_idf_parametrize_basic(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    """Test basic parametrize functionality"""
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from pytest_embedded_idf.utils import idf_parametrize

    @idf_parametrize('param', ['value1', 'value2'], indirect=True)
    def test_func():
        pass

    markers = [mark for mark in test_func.pytestmark if mark.name == 'parametrize']
    assert len(markers) == 1
    assert markers == [
        (
            pytest.mark.parametrize(
                'param',
                [pytest.param(*('value1',), marks=(), id=None), pytest.param(*('value2',), marks=(), id=None)],
                indirect=True,
            )
        ).mark
    ]  # Changed to indirect=True
    assert markers[0].args[0] == 'param'
    assert markers[0].args[1] == [
        pytest.param(*('value1',), marks=(), id=None),
        pytest.param(*('value2',), marks=(), id=None),
    ]


def test_idf_parametrize_with_target(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    """Test parametrize with target expansion"""
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from esp_bool_parser import SUPPORTED_TARGETS
    from pytest_embedded_idf.utils import idf_parametrize

    @idf_parametrize('target,param', [('supported_targets', 'something')], indirect=True)
    def test_func():
        pass

    markers = [mark for mark in test_func.pytestmark if mark.name == 'parametrize']
    assert len(markers) == 1

    expected_params = [pytest.param(*(target, 'something'), marks=(), id=None) for target in SUPPORTED_TARGETS]

    assert markers == [(pytest.mark.parametrize('target,param', expected_params, indirect=True)).mark]

    assert markers[0].args[0] == 'target,param'
    assert markers[0].args[1] == expected_params


def test_idf_parametrize_with_marker(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    """Test parametrize with pytest markers"""
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from pytest_embedded_idf.utils import idf_parametrize

    mark = pytest.mark.skip(reason='test')

    @idf_parametrize('param,markers', [('something', mark)], indirect=True)
    def test_func():
        pass

    markers = [mark for mark in test_func.pytestmark if mark.name == 'parametrize']
    assert len(markers) == 1

    expected_params = [pytest.param(*('something',), marks=(mark,), id=None)]

    assert markers == [(pytest.mark.parametrize('param', expected_params, indirect=True)).mark]

    assert markers[0].args[0] == 'param'
    assert markers[0].args[1] == expected_params


def test_idf_parametrize_with_markers(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    """Test parametrize with pytest markers"""
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from pytest_embedded_idf.utils import idf_parametrize

    marks = (pytest.mark.skip(reason='test'), pytest.mark.skip(reason='wait for fix'))

    @idf_parametrize('param,markers', [('something', marks)], indirect=True)
    def test_func():
        pass

    markers = [mark for mark in test_func.pytestmark if mark.name == 'parametrize']
    assert len(markers) == 1

    expected_params = [pytest.param(*('something',), marks=marks, id=None)]

    assert markers == [(pytest.mark.parametrize('param', expected_params, indirect=True)).mark]

    assert markers[0].args[0] == 'param'
    assert markers[0].args[1] == expected_params


def test_idf_parametrize_invalid_params(testdir, copy_mock_esp_idf, monkeypatch):  # noqa: ARG001
    """Test parametrize with invalid parameters"""
    monkeypatch.setenv('IDF_PATH', str(testdir))
    from pytest_embedded_idf.utils import idf_parametrize

    with pytest.raises(ValueError):

        @idf_parametrize('', [])
        def test_func():
            pass
