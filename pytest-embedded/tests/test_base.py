import os
import xml.etree.ElementTree as ET

import pytest


def test_help(testdir):
    result = testdir.runpytest(
        '--help'
    )

    result.stdout.fnmatch_lines([
        'embedded:',
    ])


def test_services(testdir):
    testdir.makepyfile("""
        import pytest
        import pexpect

        def class_names(services):
            classes = services[0]
            return set([cls.__name__ for cls in classes.values()])

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
        import pytest
        import pexpect

        def test_fixtures_test_file_name(test_file_path):
            assert test_file_path.endswith('test_fixtures.py')

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
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
    )

    result.assert_outcomes(passed=5)


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
                dut[0].expect('not been redirected', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--count', 2,
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}'
                      f'|'
                      f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}',
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


@pytest.mark.parametrize('parallel_count, parallel_index, res', [
    (5, 1, 1),
    (5, 6, 0),
    (4, 1, 2),
    (4, 3, 1),
    (4, 4, 0),
    (3, 1, 2),
    (3, 3, 1),
    (2, 1, 3),
    (2, 2, 2),
])
def test_parallel_run(testdir, parallel_count, parallel_index, res):
    from pytest_embedded.plugin import PytestEmbedded

    fake_items = [1, 2, 3, 4, 5]
    fake_plugin = PytestEmbedded(parallel_count, parallel_index)
    fake_plugin.pytest_collection_modifyitems(fake_items)  # noqa
    assert len(fake_items) == res


def test_expect(testdir):
    testdir.makepyfile(r"""
        import re
        import threading
        import time
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


        def test_expect_from_timeout(dut):
            def write_bytes():
                for _ in range(5):
                    dut.write('1')
                    time.sleep(3)

            write_thread = threading.Thread(target=write_bytes, daemon=True)
            write_thread.start()

            res = dut.expect(pexpect.TIMEOUT, timeout=5)
            assert res == b'11'


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

    result.assert_outcomes(passed=11)


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
                -------------------
                4 Tests 3 Failures 0 Ignored
                FAIL
            '''
                )
            )
            dut.expect_unity_test_output()

            assert len(dut.testsuite.testcases) == 4
            assert dut.testsuite.attrs['failures'] == 3
            assert dut.testsuite.testcases[0].attrs['message'] == 'Expected 2 was 1'
            assert dut.testsuite.testcases[1].attrs['message'] == 'Expected 1 was 2'
            assert dut.testsuite.testcases[3].attrs['message'] == 'Expected 3 was 4'


        def test_expect_unity_test_output_fixture(dut):
            dut.write(
                inspect.cleandoc(
                    '''
                TEST(group, test_case)foo.c:100::FAIL:Expected 2 was 1
                TEST(group, test_case_2)foo.c:101::FAIL:Expected 1 was 2
                TEST(group, test case 3)foo bar.c:102::PASS
                TEST(group, test case 4)foo bar.c:103::FAIL:Expected 3 was 4
                -------------------
                4 Tests 3 Failures 0 Ignored
                FAIL
            '''
                )
            )
            dut.expect_unity_test_output()

            assert len(dut.testsuite.testcases) == 4
            assert dut.testsuite.attrs['failures'] == 3
            assert dut.testsuite.testcases[0].attrs['message'] == 'Expected 2 was 1'
            assert dut.testsuite.testcases[1].attrs['message'] == 'Expected 1 was 2'
            assert dut.testsuite.testcases[3].attrs['message'] == 'Expected 3 was 4'
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

        def test_expect_unity_test_output(dut):
            dut.write(output)
            dut.expect_unity_test_output()

        @pytest.mark.parametrize('count', [2], indirect=True)
        def test_expect_unity_test_output_multi_dut(dut):
            dut_0 = dut[0]
            dut_1 = dut[1]

            dut_0.write(output)
            dut_1.write(output)
            dut_0.expect_unity_test_output()
            dut_1.expect_unity_test_output()
    """)

    result = testdir.runpytest('--junitxml', 'report.xml')

    result.assert_outcomes(failed=2)

    junit_report = ET.parse('report.xml').getroot()[0]

    assert junit_report.attrib['errors'] == '0'
    assert junit_report.attrib['failures'] == '9'
    assert junit_report.attrib['skipped'] == '0'
    assert junit_report.attrib['tests'] == '12'

    case_names = [
        'test_case',
        'test_case_2',
        'test case 3',
        'test case 4',
    ]
    required_names = case_names[:]
    for dut in ['dut-0', 'dut-1']:
        required_names.extend([f'{case_name} [{dut}]' for case_name in case_names])

    all_case_names = [item.attrib['name'] for item in junit_report]
    for required_name in required_names:
        assert required_name in all_case_names
