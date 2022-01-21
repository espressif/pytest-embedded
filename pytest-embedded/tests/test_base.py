import os

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
                ('idf,esp', {'IdfApp', 'IdfSerial', 'SerialDut'}),
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
    from pytest_embedded.plugin import pytest_collection_modifyitems

    class FakeObject:
        def __init__(self, _count, _index):
            self.parallel_count = _count
            self.parallel_index = _index

    class FakeConfig:
        def __init__(self, _count, _index):
            self.option = FakeObject(_count, _index)

    config = FakeConfig(parallel_count, parallel_index)
    items = [1, 2, 3, 4, 5]

    pytest_collection_modifyitems(config, items)  # noqa
    assert len(items) == res


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
                    time.sleep(2)

            write_thread = threading.Thread(target=write_bytes, daemon=True)
            write_thread.start()

            res = dut.expect(pexpect.TIMEOUT, timeout=3)
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


        def test_expect_unity_test_output_basic(dut):
            dut.write(
                inspect.cleandoc(
                    '''
                foo.c:100:test_case:FAIL:Expected 2 was 1
                foo.c:101:test_case_2:FAIL:Expected 1 was 2
                -------------------
                2 Tests 2 Failures 0 Ignored
                FAIL
            '''
                )
            )
            dut.expect_unity_test_output()

            assert len(dut.testsuite.testcases) == 2
            assert dut.testsuite.attrs['failures'] == 2
            assert dut.testsuite.testcases[0].attrs['message'] == 'Expected 2 was 1'
            assert dut.testsuite.testcases[1].attrs['message'] == 'Expected 1 was 2'


        def test_expect_unity_test_output_fixture(dut):
            dut.write(
                inspect.cleandoc(
                    '''
                TEST(group, test_case):foo.c:100::FAIL:Expected 2 was 1
                TEST(group, test_case_2):foo.c:101::FAIL:Expected 1 was 2
                -------------------
                2 Tests 2 Failures 0 Ignored
                FAIL
            '''
                )
            )
            dut.expect_unity_test_output()

            assert len(dut.testsuite.testcases) == 2
            assert dut.testsuite.attrs['failures'] == 2
            assert dut.testsuite.testcases[0].attrs['message'] == 'Expected 2 was 1'
            assert dut.testsuite.testcases[1].attrs['message'] == 'Expected 1 was 2'


        def test_expect_unity_test_output_fail_at_last(dut):
            dut.write(
                inspect.cleandoc(
                    '''
                TEST(group, test_case):foo.c:100::FAIL:Expected 2 was 1
                TEST(group, test_case_2):foo.c:101::FAIL:Expected 1 was 2
                TEST(group, test_case_3):foo.c:102::PASS
                -------------------
                3 Tests 2 Failures 0 Ignored
                FAIL
            '''
                )
            )
            dut.expect_unity_test_output()

            assert len(dut.testsuite.testcases) == 3
            assert dut.testsuite.attrs['failures'] == 2
            assert dut.testsuite.testcases[0].attrs['message'] == 'Expected 2 was 1'
            assert dut.testsuite.testcases[1].attrs['message'] == 'Expected 1 was 2'
       """)

    result = testdir.runpytest()

    result.assert_outcomes(passed=8, failed=3)
