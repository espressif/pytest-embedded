import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


def test_help(testdir):
    result = testdir.runpytest('--help')

    result.stdout.fnmatch_lines(
        [
            'embedded:',
        ]
    )


def test_services(testdir):
    testdir.makepyfile("""
        import pytest
        import pexpect

        def class_names(services):
            return set([cls.__name__ for cls in services.classes.values()])

        @pytest.fixture
        def _classes(request):
            return request.param

        @pytest.mark.parametrize(
            'embedded_services,_classes', [
                ('serial', {'App', 'Serial', 'SerialDut'}),
                ('esp', {'App', 'EspSerial', 'SerialDut'}),
                ('idf', {'IdfApp', 'Dut'}),
                ('idf,serial', {'IdfApp', 'Serial', 'SerialDut'}),
                ('idf,esp', {'IdfApp', 'IdfSerial', 'IdfDut'}),
                ('idf,qemu', {'QemuApp', 'Qemu', 'QemuDut'}),
                ('arduino,esp', {'ArduinoApp', 'ArduinoSerial', 'SerialDut'}),
            ],
            indirect=True
        )
        def test_services(_fixture_classes_and_options, _classes):
            assert class_names(_fixture_classes_and_options) == _classes
    """)

    result = testdir.runpytest()

    result.assert_outcomes(passed=7)


def test_fixtures(testdir):
    testdir.makepyfile("""
        import os
        import pytest
        import pexpect
        import tempfile

        def test_fixtures_root_logdir(session_root_logdir):
            assert session_root_logdir == os.getcwd()
            assert session_root_logdir != tempfile.gettempdir()

        def test_fixtures_test_file_name(test_file_path, session_root_logdir):
            assert test_file_path.endswith('test_fixtures.py')
            assert test_file_path.startswith(session_root_logdir)

        def test_fixtures_test_case_name(test_case_name):
            assert test_case_name == 'test_fixtures_test_case_name'

        def test_fixtures_app(app):
            assert app.app_path.endswith('hello_world_esp32')

        def test_fixtures_dut(dut):
            assert dut.app.app_path.endswith('hello_world_esp32')

        def test_fixture_redirect(pexpect_proc, dut, redirect):
            with redirect():
                print('redirect to pexpect_proc')

            pexpect_proc.expect('redirect')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('redirect', timeout=1)
            dut.expect('to pexpect_proc')

            print('not been redirected')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('not been redirected', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--root-logdir',
        os.getcwd(),
    )

    result.assert_outcomes(passed=6)


def test_multi_count_fixtures(testdir):
    testdir.makepyfile("""
        import pytest
        import pexpect

        def test_fixtures_test_file_name(test_file_path):
            assert test_file_path.endswith('test_multi_count_fixtures.py')

        def test_fixtures_test_case_name(test_case_name):
            assert test_case_name == 'test_fixtures_test_case_name'

        def test_fixtures_app(app):
            assert app[0]
            assert app[1]
            assert app[0].app_path.endswith('hello_world_esp32')
            assert app[1].app_path.endswith('hello_world_esp32c3')

        def test_fixtures_dut(dut):
            assert dut[0].app.app_path.endswith('hello_world_esp32')
            assert dut[1].app.app_path.endswith('hello_world_esp32c3')

        def test_fixture_redirect(dut, redirect):
            with redirect[1]():
                print('been redirected')
            dut[1].expect('been redirected')

            with pytest.raises(pexpect.TIMEOUT):
                dut[0].expect('been redirected', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--count',
        2,
        '--app-path',
        f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}|{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
    )

    result.assert_outcomes(passed=5)


def test_default_app_path(testdir):
    testdir.makepyfile(f"""
        import pytest
        import pexpect

        def test_default_app_path(app):
            assert app.app_path == r'{testdir.tmpdir}'
    """)

    result = testdir.runpytest()

    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    'parallel_count, parallel_index, res',
    [
        (5, 1, 1),
        (5, 6, 0),
        (4, 1, 2),
        (4, 3, 1),
        (4, 4, 0),
        (3, 1, 2),
        (3, 3, 1),
        (2, 1, 3),
        (2, 2, 2),
    ],
)
def test_parallel_run(testdir, parallel_count, parallel_index, res):
    testdir.makepyfile(r"""
        def test_1(dut): pass
        def test_2(dut): pass
        def test_3(dut): pass
        def test_4(dut): pass
        def test_5(dut): pass
    """)

    result = testdir.runpytest(
        '--parallel-count',
        parallel_count,
        '--parallel-index',
        parallel_index,
    )

    result.assert_outcomes(passed=res)


def test_expect(testdir):
    testdir.makepyfile(r"""
        import re
        import pexpect
        import inspect
        import pytest
        import os

        def test_expect(dut):
            dut.write('this would be redirected')

            dut.expect(b'this')
            dut.expect('would')
            dut.expect('[be]{2}')
            dut.expect(re.compile(b'redirected'))

        def test_expect_return_value(redirect, dut):
            # here we use fixture `redirect` to write the sys.stdout to dut
            with redirect():
                print('this would be redirected')

            res = dut.expect('this (would) be ([cdeirt]+)')
            assert res.group() == b'this would be redirected'
            assert res.group(1) == b'would'
            assert res.group(2).decode('utf-8') == 'redirected'

        def test_expect_from_eof_at_first(dut):
            dut.write('this would be redirected')

            # close the pexpect process to generate an EOF
            dut.pexpect_proc.terminate()

            res = dut.expect(pexpect.EOF, timeout=None)
            assert res == b''

        def test_expect_from_eof_current_buffer(dut):
            dut.write('this would be redirected')
            dut.expect('this')

            # close the pexpect process to generate an EOF
            dut.pexpect_proc.terminate()

            res = dut.expect(pexpect.EOF, timeout=None)
            assert res == b' would be redirected'

        def test_expect_from_list(dut):
            dut.write('this would be redirected')

            pattern_list = ['this', b'would', '[be]+', re.compile(b'redirected')]

            for _ in range(4):
                dut.expect(pattern_list)

        def test_expect_exact(dut):
            dut.write('this would be redirected')

            dut.expect_exact('this would')
            dut.expect_exact(b'be redirected')

        def test_expect_exact_from_list(dut):
            dut.write('this would be redirected')

            pattern_list = ['this would', b'be redirected']

            for _ in range(2):
                dut.expect_exact(pattern_list)

        def test_expect_exact_all(dut):
            dut.write('this would be redirected')

            pattern_list = [b'be redirected', 'this would']  # reverse it

            res = dut.expect_exact(pattern_list, expect_all=True)
            assert res == [b'this would', b'be redirected']

        def test_expect_all(dut):
            dut.write('this would be redirected')

            pattern_list = [pexpect.TIMEOUT, 'redirect', '[be]{2}', 'would', 'this']  # reverse it

            res = dut.expect(pattern_list, expect_all=True, timeout=1)
            assert (res[0].group(), res[1].group(), res[2].group(), res[3].group(), res[4]) == (
                b'this',
                b'would',
                b'be',
                b'redirect',
                b'ed',
            )

        def test_expect_all_failed(dut):
            dut.write('this would be redirected')

            pattern_list = ['foobar', 'redirect', '[be]{2}', 'would', 'this']  # reverse it

            with pytest.raises(pexpect.TIMEOUT) as e:
                dut.expect(pattern_list, expect_all=True, timeout=1)

            assert e.value.value.startswith('Not found "[\'foobar\']"')
    """)

    result = testdir.runpytest()

    result.assert_outcomes(passed=10)


def test_expect_from_timeout(testdir):
    testdir.makepyfile(r"""
        import threading
        import time
        import pexpect

        def test_expect_from_timeout(msg_queue, dut):
            def write_bytes():
                for _ in range(5):
                    msg_queue.write('1')
                    time.sleep(1.5)

            write_thread = threading.Thread(target=write_bytes, daemon=True)
            write_thread.start()

            res = dut.expect(pexpect.TIMEOUT, timeout=4)
            assert res == b'111'
    """)

    result = testdir.runpytest('-s')

    result.assert_outcomes(passed=1)


def test_expect_unity_test_ouput(testdir, capsys):
    testdir.makepyfile(r"""
        import pytest
        import inspect

        def test_expect_unity_test_output_basic(dut):
            dut.write(
                inspect.cleandoc(
                    '''
                foo.c:100:test_case:FAIL:Expected 2 was 1
                foo.c:101:test_case_2:FAIL:Expected 1 was 2
                foo bar.c:102:test case 3:PASS
                foo bar.c:103:test case 4:FAIL:Expected 3 was 4
                foo bar.c:103:test case: 5:FAIL:Expected 3 was 4
                -------------------
                5 Tests 4 Failures 0 Ignored
                FAIL
            '''
                )
            )
            dut.expect_unity_test_output()

            assert len(dut.testsuite.testcases) == 5
            assert dut.testsuite.attrs['failures'] == 4
            assert dut.testsuite.testcases[0].attrs['message'] == 'Expected 2 was 1'
            assert dut.testsuite.testcases[1].attrs['message'] == 'Expected 1 was 2'
            assert dut.testsuite.testcases[3].attrs['message'] == 'Expected 3 was 4'
            assert dut.testsuite.testcases[4].name == 'test case: 5'
            assert dut.testsuite.testcases[4].attrs['message'] == 'Expected 3 was 4'


        def test_expect_unity_test_output_fixture(dut):
            dut.write(
                inspect.cleandoc(
                    '''
                TEST(group, test_case)foo.c:100::FAIL:Expected 2 was 1
                TEST(group, test_case_2)foo.c:101::FAIL:Expected 1 was 2
                TEST(group, test case 3)foo bar.c:102::PASS
                TEST(group, test case 4)foo bar.c:103::FAIL:Expected 3 was 4
                TEST(group, test case: 5)foo bar.c:103::FAIL:Expected 3 was 4
                -------------------
                5 Tests 4 Failures 0 Ignored
                FAIL
            '''
                )
            )
            dut.expect_unity_test_output()

            assert len(dut.testsuite.testcases) == 5
            assert dut.testsuite.attrs['failures'] == 4
            assert dut.testsuite.testcases[0].attrs['message'] == 'Expected 2 was 1'
            assert dut.testsuite.testcases[1].attrs['message'] == 'Expected 1 was 2'
            assert dut.testsuite.testcases[3].attrs['message'] == 'Expected 3 was 4'
            assert dut.testsuite.testcases[4].name == 'test case: 5'
            assert dut.testsuite.testcases[4].attrs['message'] == 'Expected 3 was 4'
    """)

    result = testdir.runpytest()

    result.assert_outcomes(failed=2)

    assert capsys.readouterr().out.count("raise AssertionError('Unity test failed')") == 2


def test_expect_unity_test_output_multi_dut(testdir):
    testdir.makepyfile(r"""
        import pytest
        import inspect

        output = inspect.cleandoc(
                '''
            TEST(group, test_case)foo.c:100::FAIL:Expected 2 was 1
            TEST(group, test_case_2)foo.c:101::FAIL:Expected 1 was 2
            TEST(group, test case 3)foo bar.c:102::PASS
            TEST(group, test case 4)foo bar.c:103::FAIL:Expected 3 was 4
            -------------------
            4 Tests 3 Failures 0 Ignored
            FAIL
        ''')

        @pytest.mark.parametrize('count', [2], indirect=True)
        def test_expect_unity_test_output_multi_dut(dut):
            dut_0 = dut[0]
            dut_1 = dut[1]

            dut_0.write(output)
            dut_1.write(output)
            dut_0.expect_unity_test_output()
            dut_1.expect_unity_test_output()

        @pytest.mark.parametrize('count', [2], indirect=True)
        def test_expect_unity_test_output_multi_dut_record_1(dut):
            dut_1 = dut[1]
            dut_1.write(output)
            dut_1.expect_unity_test_output()
    """)

    result = testdir.runpytest('--junitxml', 'report.xml')

    try:
        result.assert_outcomes(failed=2)
    except ValueError:
        pass

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '9'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '12'

    assert junit_report[0].get('name') == 'test_case'
    assert junit_report[0].find('failure') is not None
    assert junit_report[1].get('name') == 'test_case_2'
    assert junit_report[1].find('failure') is not None
    assert junit_report[2].get('name') == 'test case 3'
    assert junit_report[2].find('failure') is None
    assert junit_report[3].get('name') == 'test case 4'
    assert junit_report[3].find('failure') is not None

    assert junit_report[4].get('name') == 'test_case'
    assert junit_report[4].find('failure') is not None
    assert junit_report[5].get('name') == 'test_case_2'
    assert junit_report[5].find('failure') is not None
    assert junit_report[6].get('name') == 'test case 3'
    assert junit_report[6].find('failure') is None
    assert junit_report[7].get('name') == 'test case 4'
    assert junit_report[7].find('failure') is not None

    assert junit_report[8].get('name') == 'test_case'
    assert junit_report[8].find('failure') is not None
    assert junit_report[9].get('name') == 'test_case_2'
    assert junit_report[9].find('failure') is not None
    assert junit_report[10].get('name') == 'test case 3'
    assert junit_report[10].find('failure') is None
    assert junit_report[11].get('name') == 'test case 4'
    assert junit_report[11].find('failure') is not None


def test_expect_unity_test_output_multi_dut_with_illegal_chars(testdir):
    testdir.makepyfile(r"""
        import pytest
        import inspect

        output1 = inspect.cleandoc(
                u'''
            TEST(group, test_case_1)foo.c:100::FAIL:Expected 2 \x00 was 1
            -------------------
            4 Tests 3 Failures 0 Ignored
            FAIL
        ''')
        output2 = inspect.cleandoc(
                u'''
            TEST(group, test_case_2)foo.c:100::FAIL:Expected 2 \x00 was 1
            -------------------
            5 Tests 2 Failures 0 Ignored
            FAIL
        ''')

        @pytest.mark.parametrize('count', [2], indirect=True)
        def test_expect_unity_test_output_multi_dut_with_illegal_chars(dut):
            dut_0 = dut[0]
            dut_1 = dut[1]

            dut_0.write(output1)
            dut_1.write(output2)
            dut_0.expect_unity_test_output()
            dut_1.expect_unity_test_output()
    """)

    result = testdir.runpytest('--app-path', f'{testdir.tmpdir}/foo|{testdir.tmpdir}/bar', '--junitxml', 'report.xml')

    try:
        result.assert_outcomes(failed=1)
    except ValueError:
        pass

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '2'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '2'

    assert junit_report[0].get('name') == 'test_case_1'
    assert junit_report[0].find('failure') is not None
    assert junit_report[0].get('app_path') == f'{testdir.tmpdir}/foo'
    assert junit_report[1].get('name') == 'test_case_2'
    assert junit_report[1].find('failure') is not None
    assert junit_report[1].get('app_path') == f'{testdir.tmpdir}/bar'


def test_expect_before_match(testdir):
    testdir.makepyfile(r"""
        import pexpect

        def test_expect_before_match(dut):
            dut.write('this would be redirected')

            res = dut.expect('would', return_what_before_match=True)
            assert res == b'this '

            res = dut.expect_exact('be ', return_what_before_match=True)
            assert res == b' '

            res = dut.expect('ected', return_what_before_match=True)
            assert res == b'redir'
    """)

    result = testdir.runpytest()

    result.assert_outcomes(passed=1)


def test_duplicate_stdout_popen(testdir):
    testdir.makepyfile(r"""
        import pytest
        import pexpect
        import sys
        from pytest_embedded.log import DuplicateStdoutPopen

        def test_duplicate_stdout_popen(dut, msg_queue):
            p = DuplicateStdoutPopen(msg_queue, [sys.executable, '-c', 'while True: a = input(); print(a)'])
            p.write('foo')
            dut.expect('foo')

            p.write('bar')
            dut.expect('bar')

            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo', timeout=1)
     """)

    result = testdir.runpytest('-s')

    result.assert_outcomes(passed=1)


def test_set_log_extension(testdir):
    testdir.makepyfile(r"""
        import pytest

        @pytest.mark.parametrize('count', [2], indirect=True)
        @pytest.mark.parametrize('logfile_extension', [
            '.log|.txt',
        ], indirect=True)
        def test_set_log_extension(dut):
            dut[0].write('foo')
            dut[0].expect_exact('foo')

            dut[1].write('bar')
            dut[1].expect_exact('bar')
    """)
    result = testdir.runpytest('--root-logdir', testdir.tmpdir)
    result.assert_outcomes(passed=1)

    for logfile in Path(testdir.tmpdir).glob('**/dut*.log'):
        assert logfile.parts[-1] == 'dut-0.log'

    for txtfile in Path(testdir.tmpdir).glob('**/dut*.txt'):
        assert txtfile.parts[-1] == 'dut-1.txt'


def test_duplicate_case_name(testdir, capsys):
    testdir.makepyfile(
        test_duplicate_name_one=r"""
        def test_duplicate_case():
            pass
    """
    )
    testdir.makepyfile(
        test_duplicate_name_two="""
            def test_duplicate_case():
                pass
        """
    )
    testdir.runpytest('--check-duplicates', 'y')

    assert "ValueError: Duplicated test function names: ['test_duplicate_case']" in capsys.readouterr().out


def test_duplicate_module_name(testdir, capsys):
    test_sub_dir = str(testdir.mkpydir('test_dir'))
    dup_module_path = testdir.makepyfile(
        test_duplicate_module=r"""
            def test_duplicate_one():
                pass
        """
    )
    os.rename(f'{dup_module_path}', os.path.join(test_sub_dir, dup_module_path.basename))
    testdir.makepyfile(
        test_duplicate_module=r"""
                    def test_duplicate_two():
                        pass
                """
    )
    testdir.runpytest('--check-duplicates', 'y')

    assert "ValueError: Duplicated test scripts: ['test_duplicate_module.py']" in capsys.readouterr().out


@pytest.mark.temp_disable_packages('pytest_embedded_serial', 'pytest_embedded_idf')
def test_temp_disable_packages():
    with pytest.raises(ImportError):
        import pytest_embedded_serial.serial

    with pytest.raises(ImportError):
        import pytest_embedded_serial  # noqa

    with pytest.raises(ImportError):
        import pytest_embedded_idf  # noqa


@pytest.mark.temp_disable_packages(
    'pytest_embedded_serial',
    'pytest_embedded_serial_esp',
    'pytest_embedded_idf',
    'pytest_embedded_qemu',
    'pytest_embedded_jtag',
    'pytest_embedded_arduino',
)
def test_quick_example(testdir):
    testdir.makepyfile(r"""
    from pytest_embedded import Dut
    import pytest

    def test_quick_example(redirect, dut: Dut):
        with pytest.raises(ImportError):
            import pytest_embedded_serial

        with redirect():
            print('this would be redirected')

        dut.expect('this')
        dut.expect_exact('would')
        dut.expect('[be]{2}')
        dut.expect_exact('redirected')
    """)
    result = testdir.runpytest('--root-logdir', testdir.tmpdir)
    result.assert_outcomes(passed=1)


@pytest.mark.skip
def test_unclosed_file_handler(testdir):
    """
    select only support fd < FD_SETSIZE (1024)

    Related Links:
        - https://github.com/python/cpython/blob/v3.11.1/Include/fileobject.h#L37
        - https://man7.org/linux/man-pages/man2/select.2.html
    """
    testdir.makepyfile(r"""
    import pytest

    @pytest.mark.parametrize("test_input", range(0, 1024))
    def test_unclosed_file_handler(test_input, dut):
        dut[0].write("foo")
        assert test_input == test_input
    """)
    result = testdir.runpytest(
        '--embedded-services',
        'serial',
        '--count',
        '3',
        '--port',
        '/dev/ttyUSB0|/dev/ttyUSB1|/dev/ttyUSB2',
        '-x',  # fail at the first fail
    )
    result.assert_outcomes(passed=1024)


def test_check_app_path_for_python_case(testdir):
    testdir.makepyfile(r"""
    import pytest


    def test_foo(dut):
        dut.write('foo')
        dut.expect_exact('foo')
    """)

    result = testdir.runpytest(
        '--junitxml',
        'report.xml',
        '--app-path',
        '/tmp/foo',
    )
    result.assert_outcomes(passed=1)

    junit_report = ET.parse('report.xml').getroot()[0]
    assert junit_report[0].get('app_path') == '/tmp/foo'

    result = testdir.runpytest(
        '--junitxml',
        'report.xml',
    )
    result.assert_outcomes(passed=1)

    junit_report = ET.parse('report.xml').getroot()[0]
    assert junit_report[0].get('app_path') == str(testdir)


class TestTargetMarkers:
    def test_add_target_as_marker_with_amount(self, pytester):
        pytester.makepyfile("""
            import pytest
            @pytest.mark.parametrize('target,count', [
                ('esp32|esp8266', 2),
                ('esp32', 2),
                ('esp32|esp8266|esp32s2', 3),
            ], indirect=True)
            def test_example(target):
                pass
        """)

        result = pytester.runpytest('--add-target-as-marker-with-amount', 'y', '-vvvv')

        result.assert_outcomes(passed=3)
        result.stdout.fnmatch_lines(
            [
                '*Unknown pytest.mark.esp32+esp8266 - is this a typo?*',
                '*Unknown pytest.mark.esp32_2 - is this a typo?*',
                '*Unknown pytest.mark.esp32+esp32s2+esp8266 - is this a typo?*',
            ]
        )

    def test_no_target_no_marker(self, pytester):
        pytester.makepyfile("""
            def test_example():
                pass
        """)

        result = pytester.runpytest(
            '--add-target-as-marker-with-amount', 'y', '--embedded-services', 'esp', '--target', 'esp32'
        )

        result.assert_outcomes(passed=1)
        assert 'Unknown pytest.mark.esp32 - is this a typo?' not in result.stdout.str()
