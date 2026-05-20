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

        def test_expect_no_matching_list(dut):  # fail
            dut.write('Hello world!')
            dut.write('Restarting')
            dut.expect('world!', not_matching=[re.compile("Hell"), "Hello"])

        def test_expect_no_matching_word(dut):  # fail
            dut.write('Hello world!')
            dut.write('Restarting')
            dut.expect('Restarting', not_matching="Hello world!")

        def test_expect_no_matching_word_pass(dut):
            dut.write('Hello world!')
            dut.write('Restarting')
            dut.expect('Restarting', not_matching="Hello world!333")

        def test_expect_no_matching_word_pass_rest(dut):
            dut.write('Hello world!')
            dut.write('Restarting')
            dut.expect('Hello world', not_matching="Restarting")

        def test_expect_exact_no_matching_list(dut):  # fail
            dut.write('Hello world!')
            dut.write('Restarting')
            dut.expect_exact('world!', not_matching=["Hell1", "Hello"])

        def test_expect_exact_no_matching_word(dut):  # fail
            dut.write('Hello world!')
            dut.write('Restarting')
            dut.expect_exact('Restarting', not_matching="Hello world!")

        def test_expect_exact_no_matching_word_pass(dut):
            dut.write('Hello world!')
            dut.write('Restarting')
            dut.expect_exact('Restarting', not_matching="Hello world!333")

        def test_expect_exact_no_matching_word_pass_rest(dut):
            dut.write('Hello world!')
            dut.write('Restarting')
            dut.expect_exact('Hello world', not_matching="Restarting")
    """)

    result = testdir.runpytest()

    result.assert_outcomes(failed=4, passed=14)


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


def test_log_metric_with_path(pytester):
    metric_file = pytester.path / 'metrics.txt'
    pytester.makepyfile("""
        def test_metric(log_metric):
            log_metric('my_metric', 123.45, label1='value1', target='esp32')
    """)

    result = pytester.runpytest(f'--metric-path={metric_file}')
    result.assert_outcomes(passed=1)

    with open(metric_file) as f:
        content = f.read()

    assert content == 'my_metric{label1="value1",target="esp32"} 123.45\n'


def test_log_metric_without_path(pytester):
    pytester.makepyfile("""
        import pytest

        def test_metric_no_path(log_metric):
            with pytest.warns(UserWarning, match='`--metric-path` is not specified, `log_metric` does nothing.'):
                log_metric('my_metric', 123.45)
    """)

    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


# ---------------------------------------------------------------------------
# Tests for the stdout-lock feature (_stdout_lock / set_stdout_lock / _listen)
# ---------------------------------------------------------------------------


def test_set_stdout_lock():
    """set_stdout_lock updates the module-level _STDOUT_LOCK variable."""
    import pytest_embedded.dut_factory as m
    from pytest_embedded.dut_factory import set_stdout_lock

    original = m._STDOUT_LOCK
    try:
        sentinel = object()
        set_stdout_lock(sentinel)
        assert m._STDOUT_LOCK is sentinel

        set_stdout_lock(None)
        assert m._STDOUT_LOCK is None
    finally:
        set_stdout_lock(original)


def test_listen_no_data_loss_without_lock(tmp_path):
    """_listen writes every queued message to the logfile when no lock is used."""
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    messages = [f'line_{i}\n'.encode() for i in range(20)]

    p = _ctx.Process(target=_listen, args=(q, logfile), kwargs={'with_timestamp': False})
    p.start()
    try:
        for msg in messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if all(msg in content for msg in messages):
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)
        assert p.exitcode is not None, 'listener process did not terminate'

    content = open(logfile, 'rb').read()
    for msg in messages:
        assert msg in content, f'{msg!r} missing from logfile'


def test_listen_no_data_loss_with_lock(tmp_path):
    """_listen writes every queued message to the logfile when a Manager lock is used."""
    import multiprocessing
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    messages = [f'line_{i}\n'.encode() for i in range(20)]

    manager = multiprocessing.Manager()
    try:
        lock = manager.Lock()
        p = _ctx.Process(
            target=_listen,
            args=(q, logfile),
            kwargs={'with_timestamp': False, '_stdout_lock': lock},
        )
        p.start()
        try:
            for msg in messages:
                q.put(msg)

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    content = open(logfile, 'rb').read()
                    if all(msg in content for msg in messages):
                        break
                except OSError:
                    pass
                time.sleep(0.05)
        finally:
            p.terminate()
            p.join(timeout=5)
            assert p.exitcode is not None, 'listener process did not terminate'
    finally:
        manager.shutdown()

    content = open(logfile, 'rb').read()
    for msg in messages:
        assert msg in content, f'{msg!r} missing from logfile'


def test_stdout_lock_concurrent_no_data_loss(tmp_path):
    """Two concurrent _listen processes sharing a Manager lock both preserve all data."""
    import multiprocessing
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile0 = str(tmp_path / 'dut0.log')
    logfile1 = str(tmp_path / 'dut1.log')
    q0 = MessageQueue()
    q1 = MessageQueue()
    messages0 = [f'dut0_line_{i}\n'.encode() for i in range(20)]
    messages1 = [f'dut1_line_{i}\n'.encode() for i in range(20)]

    manager = multiprocessing.Manager()
    try:
        lock = manager.Lock()
        p0 = _ctx.Process(
            target=_listen,
            args=(q0, logfile0),
            kwargs={'with_timestamp': False, 'count': 1, 'total': 2, '_stdout_lock': lock},
        )
        p1 = _ctx.Process(
            target=_listen,
            args=(q1, logfile1),
            kwargs={'with_timestamp': False, 'count': 2, 'total': 2, '_stdout_lock': lock},
        )
        p0.start()
        p1.start()
        try:
            # interleave writes from both DUTs to maximize lock contention
            for msg0, msg1 in zip(messages0, messages1):
                q0.put(msg0)
                q1.put(msg1)

            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                try:
                    c0 = open(logfile0, 'rb').read()
                    c1 = open(logfile1, 'rb').read()
                    if all(m in c0 for m in messages0) and all(m in c1 for m in messages1):
                        break
                except OSError:
                    pass
                time.sleep(0.05)
        finally:
            p0.terminate()
            p1.terminate()
            p0.join(timeout=5)
            p1.join(timeout=5)
            assert p0.exitcode is not None, 'dut0 listener process did not terminate'
            assert p1.exitcode is not None, 'dut1 listener process did not terminate'
    finally:
        manager.shutdown()

    c0 = open(logfile0, 'rb').read()
    c1 = open(logfile1, 'rb').read()
    for msg in messages0:
        assert msg in c0, f'{msg!r} missing from dut0 logfile'
    for msg in messages1:
        assert msg in c1, f'{msg!r} missing from dut1 logfile'


def test_multi_dut_no_data_loss(testdir):
    """In a 2-DUT test, all messages written by each DUT can be expected - nothing is dropped."""
    testdir.makepyfile(r"""
        import pytest

        @pytest.mark.parametrize('count', [2], indirect=True)
        def test_concurrent_dut_writes(dut):
            n = 15
            for i in range(n):
                dut[0].write(f'dut0_msg_{i}')
                dut[1].write(f'dut1_msg_{i}')

            for i in range(n):
                dut[0].expect_exact(f'dut0_msg_{i}')
                dut[1].expect_exact(f'dut1_msg_{i}')
    """)

    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


# ---------------------------------------------------------------------------
# Tests for echo muting (_listen mute_event / mute_patterns)
# ---------------------------------------------------------------------------


def _run_listen_with_stdout_capture(q, logfile, stdout_filepath, listen_kwargs):
    """Run _listen in a child process, redirecting module stdout to a file."""
    import pytest_embedded.dut_factory as dut_factory
    from pytest_embedded.dut_factory import _listen

    with open(stdout_filepath, 'w', encoding='utf-8') as captured:
        dut_factory._stdout = captured
        _listen(q, logfile, **listen_kwargs)


def test_listen_backwards_compat_no_mute_args(tmp_path):
    """_listen still works when called without mute_event or mute_patterns (pre-existing API)."""
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    messages = [f'compat_{i}\n'.encode() for i in range(10)]

    p = _ctx.Process(target=_listen, args=(q, logfile), kwargs={'with_timestamp': False})
    p.start()
    try:
        for msg in messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if all(msg in content for msg in messages):
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)
        assert p.exitcode is not None

    content = open(logfile, 'rb').read()
    for msg in messages:
        assert msg in content, f'{msg!r} missing from logfile'


def test_listen_mute_event_suppresses_stdout(tmp_path):
    """When mute_event is set, _listen still writes to the logfile but skips stdout."""
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    event = _ctx.Event()
    event.set()

    messages = [f'muted_line_{i}\n'.encode() for i in range(10)]

    p = _ctx.Process(
        target=_listen,
        args=(q, logfile),
        kwargs={'with_timestamp': False, 'mute_event': event},
    )
    p.start()
    try:
        for msg in messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if all(msg in content for msg in messages):
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)

    content = open(logfile, 'rb').read()
    for msg in messages:
        assert msg in content, f'{msg!r} should still be in logfile even when muted'


def test_listen_mute_event_cleared_allows_stdout(tmp_path):
    """When mute_event is cleared (default), _listen writes to both logfile and stdout."""
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    event = _ctx.Event()  # not set = not muted

    messages = [f'unmuted_{i}\n'.encode() for i in range(5)]

    p = _ctx.Process(
        target=_listen,
        args=(q, logfile),
        kwargs={'with_timestamp': False, 'mute_event': event},
    )
    p.start()
    try:
        for msg in messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if all(msg in content for msg in messages):
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)

    content = open(logfile, 'rb').read()
    for msg in messages:
        assert msg in content


def test_listen_mute_patterns_auto_mutes(tmp_path):
    """mute_patterns causes _listen to auto-mute between start/end markers; logfile is unaffected."""
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    patterns = [('<<<START>>>', '<<<END>>>')]

    all_messages = [
        b'before\n',
        b'<<<START>>>\n',
        b'muted_payload_1\n',
        b'muted_payload_2\n',
        b'<<<END>>>\n',
        b'after\n',
    ]

    p = _ctx.Process(
        target=_listen,
        args=(q, logfile),
        kwargs={'with_timestamp': False, 'mute_patterns': patterns},
    )
    p.start()
    try:
        for msg in all_messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if b'after' in content:
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)

    content = open(logfile, 'rb').read()
    for msg in all_messages:
        assert msg in content, f'{msg!r} should be in logfile regardless of muting'


def test_listen_mute_patterns_multiple_pairs(tmp_path):
    """Multiple mute_patterns pairs can be registered simultaneously."""
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    patterns = [
        ('<<<GCOV_START>>>', '<<<GCOV_END>>>'),
        ('<<<DIAG_START>>>', '<<<DIAG_END>>>'),
    ]

    all_messages = [
        b'normal_1\n',
        b'<<<GCOV_START>>>\n',
        b'gcov_data\n',
        b'<<<GCOV_END>>>\n',
        b'normal_2\n',
        b'<<<DIAG_START>>>\n',
        b'diag_data\n',
        b'<<<DIAG_END>>>\n',
        b'normal_3\n',
    ]

    p = _ctx.Process(
        target=_listen,
        args=(q, logfile),
        kwargs={'with_timestamp': False, 'mute_patterns': patterns},
    )
    p.start()
    try:
        for msg in all_messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if b'normal_3' in content:
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)

    content = open(logfile, 'rb').read()
    for msg in all_messages:
        assert msg in content


def test_listen_empty_mute_patterns_no_effect(tmp_path):
    """Empty mute_patterns tuple has no effect — same as not passing it."""
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    messages = [f'pass_through_{i}\n'.encode() for i in range(10)]

    p = _ctx.Process(
        target=_listen,
        args=(q, logfile),
        kwargs={'with_timestamp': False, 'mute_patterns': ()},
    )
    p.start()
    try:
        for msg in messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if all(msg in content for msg in messages):
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)

    content = open(logfile, 'rb').read()
    for msg in messages:
        assert msg in content


def test_listen_mute_patterns_wrong_end_does_not_unmute(tmp_path):
    """Matching startA then endB must NOT unmute — only endA should."""
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    patterns = [
        ('<<<A_START>>>', '<<<A_END>>>'),
        ('<<<B_START>>>', '<<<B_END>>>'),
    ]

    all_messages = [
        b'visible_before\n',
        b'<<<A_START>>>\n',
        b'should_be_muted\n',
        b'<<<B_END>>>\n',
        b'still_muted_after_wrong_end\n',
        b'<<<A_END>>>\n',
        b'visible_after\n',
    ]

    p = _ctx.Process(
        target=_listen,
        args=(q, logfile),
        kwargs={'with_timestamp': False, 'mute_patterns': patterns},
    )
    p.start()
    try:
        for msg in all_messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if b'visible_after' in content:
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)

    content = open(logfile, 'rb').read()
    for msg in all_messages:
        assert msg in content, f'{msg!r} must always be written to the logfile'


def test_listen_mute_patterns_split_across_chunks(tmp_path):
    """A mute pattern split across two serial chunks must still trigger muting."""
    import time

    from pytest_embedded.dut_factory import _ctx, _listen
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    q = MessageQueue()
    patterns = [('<<<START>>>', '<<<END>>>')]

    all_messages = [
        b'before\n',
        b'<<<STA',
        b'RT>>>\n',
        b'muted_payload\n',
        b'<<<EN',
        b'D>>>\n',
        b'after\n',
    ]

    p = _ctx.Process(
        target=_listen,
        args=(q, logfile),
        kwargs={'with_timestamp': False, 'mute_patterns': patterns},
    )
    p.start()
    try:
        for msg in all_messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if b'after' in content:
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)

    content = open(logfile, 'rb').read()
    for msg in all_messages:
        assert msg in content, f'{msg!r} must be in logfile'


def test_listen_mute_patterns_both_in_one_chunk(tmp_path):
    """When one chunk contains both start and end markers, payload must stay off stdout."""
    import time

    from pytest_embedded.dut_factory import _ctx
    from pytest_embedded.log import MessageQueue

    logfile = str(tmp_path / 'test.log')
    stdout_file = str(tmp_path / 'stdout.log')
    q = MessageQueue()
    patterns = [('<<<START>>>', '<<<END>>>')]

    all_messages = [
        b'before\n',
        b'<<<START>>>payload<<<END>>>\n',
        b'after\n',
    ]

    p = _ctx.Process(
        target=_run_listen_with_stdout_capture,
        args=(q, logfile, stdout_file),
        kwargs={'listen_kwargs': {'with_timestamp': False, 'mute_patterns': patterns}},
    )
    p.start()
    try:
        for msg in all_messages:
            q.put(msg)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                content = open(logfile, 'rb').read()
                if b'after' in content:
                    break
            except OSError:
                pass
            time.sleep(0.05)
    finally:
        p.terminate()
        p.join(timeout=5)

    content = open(logfile, 'rb').read()
    for msg in all_messages:
        assert msg in content, f'{msg!r} must be in logfile'

    stdout_content = open(stdout_file, encoding='utf-8').read()
    assert 'before' in stdout_content
    assert 'after' in stdout_content
    assert 'payload' not in stdout_content
    assert '<<<START>>>' not in stdout_content
    assert '<<<END>>>' not in stdout_content


# ---------------------------------------------------------------------------
# Tests for Dut mute_echo / unmute_echo / muted_echo
# ---------------------------------------------------------------------------


def _make_dut_with_pipe(tmp_path, mute_event=None):
    """Helper: create a Dut backed by an OS pipe for unit testing."""
    import os

    from pytest_embedded.dut import Dut
    from pytest_embedded.log import MessageQueue, PexpectProcess

    rd, wr = os.pipe()
    fr = os.fdopen(rd, 'rb', 0)
    fw = os.fdopen(wr, 'wb', 0)
    proc = PexpectProcess(fr)
    q = MessageQueue()
    dut = Dut(
        pexpect_proc=proc,
        msg_queue=q,
        app=None,
        pexpect_logfile=str(tmp_path / 'dut.log'),
        test_case_name='test',
        _mute_event=mute_event,
    )
    return dut, fw


def test_dut_mute_echo_sets_event(tmp_path):
    """Dut.mute_echo() sets the event; unmute_echo() clears it."""
    from pytest_embedded.dut_factory import _ctx

    event = _ctx.Event()
    assert not event.is_set()

    dut, fw = _make_dut_with_pipe(tmp_path, mute_event=event)

    dut.mute_echo()
    assert event.is_set()

    dut.unmute_echo()
    assert not event.is_set()
    fw.close()


def test_dut_muted_echo_context_manager(tmp_path):
    """muted_echo() context manager sets event on entry, clears on exit."""
    from pytest_embedded.dut_factory import _ctx

    event = _ctx.Event()
    dut, fw = _make_dut_with_pipe(tmp_path, mute_event=event)

    assert not event.is_set()
    with dut.muted_echo():
        assert event.is_set()
    assert not event.is_set()
    fw.close()


def test_dut_mute_echo_without_event_is_noop(tmp_path):
    """mute_echo / unmute_echo are no-ops when _mute_event is None (backwards compat)."""
    dut, fw = _make_dut_with_pipe(tmp_path, mute_event=None)

    dut.mute_echo()
    dut.unmute_echo()
    with dut.muted_echo():
        pass
    fw.close()


# ---------------------------------------------------------------------------
# Tests for Dut.capture_payload / capture_payload_to_file
# ---------------------------------------------------------------------------


def test_capture_payload_returns_bytes_between_markers(tmp_path):
    """capture_payload returns the raw bytes between start and end markers."""
    import threading

    from pytest_embedded.dut import Dut
    from pytest_embedded.log import MessageQueue, PexpectProcess

    q = MessageQueue()
    logfile = str(tmp_path / 'dut.log')

    # PexpectProcess uses the file reader end for pexpect
    import os

    _pexpect_fr_rd, _pexpect_fr_wr = os.pipe()
    fr = os.fdopen(_pexpect_fr_rd, 'rb', 0)
    fw = os.fdopen(_pexpect_fr_wr, 'wb', 0)
    proc = PexpectProcess(fr)

    dut = Dut(
        pexpect_proc=proc,
        msg_queue=q,
        app=None,
        pexpect_logfile=logfile,
        test_case_name='test_cap',
        _mute_event=None,
    )

    payload = b'<<<START>>>\nHELLO_PAYLOAD\n<<<END>>>\n'

    def _write():
        import time

        time.sleep(0.2)
        fw.write(payload)
        fw.flush()

    t = threading.Thread(target=_write, daemon=True)
    t.start()

    result = dut.capture_payload('<<<START>>>', '<<<END>>>', start_timeout=5, timeout=5)
    t.join(timeout=5)
    fw.close()

    assert result is not None
    assert b'HELLO_PAYLOAD' in result


def test_capture_payload_returns_none_on_timeout(tmp_path):
    """capture_payload returns None when start marker is not seen."""
    import os

    from pytest_embedded.dut import Dut
    from pytest_embedded.log import MessageQueue, PexpectProcess

    _rd, _wr = os.pipe()
    fr = os.fdopen(_rd, 'rb', 0)
    fw = os.fdopen(_wr, 'wb', 0)
    proc = PexpectProcess(fr)

    dut = Dut(
        pexpect_proc=proc,
        msg_queue=MessageQueue(),
        app=None,
        pexpect_logfile=str(tmp_path / 'dut.log'),
        test_case_name='test_timeout',
    )

    result = dut.capture_payload('<<<NEVER>>>', '<<<END>>>', start_timeout=0.5, timeout=0.5)
    fw.close()

    assert result is None


def test_capture_payload_to_file_writes_data(tmp_path):
    """capture_payload_to_file creates a file with the captured payload."""
    import os
    import threading

    from pytest_embedded.dut import Dut
    from pytest_embedded.log import MessageQueue, PexpectProcess

    _rd, _wr = os.pipe()
    fr = os.fdopen(_rd, 'rb', 0)
    fw = os.fdopen(_wr, 'wb', 0)
    proc = PexpectProcess(fr)

    out_file = str(tmp_path / 'captured.txt')

    dut = Dut(
        pexpect_proc=proc,
        msg_queue=MessageQueue(),
        app=None,
        pexpect_logfile=str(tmp_path / 'dut.log'),
        test_case_name='test_cap_file',
        _mute_event=None,
    )

    payload = b'<<<S>>>\nDATA_LINE_1\nDATA_LINE_2\n<<<E>>>\n'

    def _write():
        import time

        time.sleep(0.2)
        fw.write(payload)
        fw.flush()

    t = threading.Thread(target=_write, daemon=True)
    t.start()

    ok = dut.capture_payload_to_file(
        '<<<S>>>',
        '<<<E>>>',
        filepath=out_file,
        start_timeout=5,
        timeout=5,
        mute=False,
        append=False,
        include_markers=True,
    )
    t.join(timeout=5)
    fw.close()

    assert ok is True
    content = open(out_file).read()
    assert '<<<S>>>' in content
    assert 'DATA_LINE_1' in content
    assert 'DATA_LINE_2' in content
    assert '<<<E>>>' in content


def test_capture_payload_to_file_append_mode(tmp_path):
    """capture_payload_to_file with append=True accumulates data across calls."""
    import os
    import threading

    from pytest_embedded.dut import Dut
    from pytest_embedded.log import MessageQueue, PexpectProcess

    _rd, _wr = os.pipe()
    fr = os.fdopen(_rd, 'rb', 0)
    fw = os.fdopen(_wr, 'wb', 0)
    proc = PexpectProcess(fr)

    out_file = str(tmp_path / 'appended.txt')

    dut = Dut(
        pexpect_proc=proc,
        msg_queue=MessageQueue(),
        app=None,
        pexpect_logfile=str(tmp_path / 'dut.log'),
        test_case_name='test_append',
        _mute_event=None,
    )

    def _write_two_payloads():
        import time

        time.sleep(0.2)
        fw.write(b'<<<S>>>\nBOOT1_DATA\n<<<E>>>\n')
        fw.flush()
        time.sleep(0.2)
        fw.write(b'<<<S>>>\nBOOT2_DATA\n<<<E>>>\n')
        fw.flush()

    t = threading.Thread(target=_write_two_payloads, daemon=True)
    t.start()

    ok1 = dut.capture_payload_to_file('<<<S>>>', '<<<E>>>', filepath=out_file, start_timeout=5, timeout=5, mute=False)
    ok2 = dut.capture_payload_to_file('<<<S>>>', '<<<E>>>', filepath=out_file, start_timeout=5, timeout=5, mute=False)
    t.join(timeout=5)
    fw.close()

    assert ok1 is True
    assert ok2 is True
    content = open(out_file).read()
    assert 'BOOT1_DATA' in content
    assert 'BOOT2_DATA' in content


def test_capture_payload_to_file_returns_false_on_timeout(tmp_path):
    """capture_payload_to_file returns False when start marker is never seen."""
    import os

    from pytest_embedded.dut import Dut
    from pytest_embedded.log import MessageQueue, PexpectProcess

    _rd, _wr = os.pipe()
    fr = os.fdopen(_rd, 'rb', 0)
    fw = os.fdopen(_wr, 'wb', 0)
    proc = PexpectProcess(fr)

    out_file = str(tmp_path / 'nodata.txt')

    dut = Dut(
        pexpect_proc=proc,
        msg_queue=MessageQueue(),
        app=None,
        pexpect_logfile=str(tmp_path / 'dut.log'),
        test_case_name='test_no_cap',
    )

    ok = dut.capture_payload_to_file(
        '<<<NEVER>>>', '<<<END>>>', filepath=out_file, start_timeout=0.5, timeout=0.5, mute=False
    )
    fw.close()

    assert ok is False
    assert not os.path.exists(out_file)


# ---------------------------------------------------------------------------
# Tests for mute_patterns / _mute_event fixtures (via testdir)
# ---------------------------------------------------------------------------


def test_mute_patterns_fixture_default(testdir):
    """The default mute_patterns fixture returns an empty tuple."""
    testdir.makepyfile("""
        def test_default_patterns(mute_patterns):
            assert mute_patterns == ()
    """)

    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_mute_event_fixture_exists(testdir):
    """The _mute_event fixture is created and is usable."""
    testdir.makepyfile("""
        def test_event_exists(_mute_event):
            assert _mute_event is not None
            assert not _mute_event.is_set()
            _mute_event.set()
            assert _mute_event.is_set()
            _mute_event.clear()
    """)

    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_mute_patterns_override_in_conftest(testdir):
    """Projects can override mute_patterns in conftest.py to register custom patterns."""
    testdir.makeconftest("""
        import pytest

        @pytest.fixture
        def mute_patterns():
            return [("<<<CUSTOM_START>>>", "<<<CUSTOM_END>>>")]
    """)
    testdir.makepyfile("""
        def test_custom_patterns(mute_patterns):
            assert len(mute_patterns) == 1
            assert mute_patterns[0] == ("<<<CUSTOM_START>>>", "<<<CUSTOM_END>>>")
    """)

    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


# ---------------------------------------------------------------------------
# Integration: mute_patterns + dut echo suppression (via testdir)
# ---------------------------------------------------------------------------


def test_mute_patterns_integration_with_dut(testdir):
    """mute_patterns auto-mutes output between markers but data still reaches pexpect."""
    testdir.makeconftest("""
        import pytest

        @pytest.fixture
        def mute_patterns():
            return [("<<<BLOCK_START>>>", "<<<BLOCK_END>>>")]
    """)
    testdir.makepyfile("""
        def test_muted_payload(dut, redirect):
            with redirect():
                print("before_marker")
                print("<<<BLOCK_START>>>")
                print("secret_payload_data")
                print("<<<BLOCK_END>>>")
                print("after_marker")

            dut.expect_exact("before_marker")
            dut.expect_exact("<<<BLOCK_START>>>")
            dut.expect_exact("secret_payload_data")
            dut.expect_exact("<<<BLOCK_END>>>")
            dut.expect_exact("after_marker")
    """)

    result = testdir.runpytest('-s')
    result.assert_outcomes(passed=1)


def test_dut_capture_payload_integration(testdir):
    """capture_payload works inside a real pytest-embedded session."""
    testdir.makepyfile("""
        import threading

        def test_capture(dut, redirect):
            def _emit():
                import time
                time.sleep(0.3)
                with redirect():
                    print("<<<CAP_START>>>")
                    print("captured_line_1")
                    print("captured_line_2")
                    print("<<<CAP_END>>>")

            t = threading.Thread(target=_emit, daemon=True)
            t.start()

            data = dut.capture_payload("<<<CAP_START>>>", "<<<CAP_END>>>", start_timeout=5, timeout=5)
            t.join(timeout=5)

            assert data is not None
            text = data.decode('utf-8', errors='replace')
            assert "captured_line_1" in text
            assert "captured_line_2" in text
    """)

    result = testdir.runpytest('-s')
    result.assert_outcomes(passed=1)


def test_backwards_compat_no_mute_patterns_no_event(testdir):
    """Tests that don't use mute_patterns or _mute_event work identically to before."""
    testdir.makepyfile("""
        def test_basic_expect(dut, redirect):
            with redirect():
                print("hello world")

            dut.expect_exact("hello world")
    """)

    result = testdir.runpytest('-s')
    result.assert_outcomes(passed=1)


def test_multi_dut_with_mute_patterns(testdir):
    """mute_patterns works correctly in multi-DUT mode without IndexError."""
    testdir.makeconftest("""
        import pytest

        @pytest.fixture
        def mute_patterns():
            return [("<<<MUTE_START>>>", "<<<MUTE_END>>>")]
    """)
    testdir.makepyfile(r"""
        import pytest

        @pytest.mark.parametrize('count', [2], indirect=True)
        def test_multi_dut_mute(dut):
            dut[0].write(b'hello_from_dut0')
            dut[1].write(b'hello_from_dut1')

            dut[0].expect_exact('hello_from_dut0')
            dut[1].expect_exact('hello_from_dut1')
    """)

    result = testdir.runpytest('-s')
    result.assert_outcomes(passed=1)


def test_multi_dut_default_mute_patterns(testdir):
    """Default empty mute_patterns does not break multi-DUT mode."""
    testdir.makepyfile(r"""
        import pytest

        @pytest.mark.parametrize('count', [2], indirect=True)
        def test_multi_dut_default(dut):
            dut[0].write(b'msg_a')
            dut[1].write(b'msg_b')

            dut[0].expect_exact('msg_a')
            dut[1].expect_exact('msg_b')
    """)

    result = testdir.runpytest('-s')
    result.assert_outcomes(passed=1)
