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
            ],
            indirect=True
        )
        def test_services(_fixture_classes_and_options, _classes):
            assert class_names(_fixture_classes_and_options) == _classes
    """)

    result = testdir.runpytest()

    result.assert_outcomes(passed=6)


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
            with redirect('prefix'):
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
            with redirect[1]('prefix'):
                print('been redirected')
            dut[1].expect('been redirected')

            with pytest.raises(pexpect.TIMEOUT):
                dut[0].expect('not been redirected', timeout=1)
    """)

    result = testdir.runpytest(
        '--count', 2,
        '--app-path', f'{os.path.join(testdir.tmpdir, "hello_world_esp32")}'
                      f'|'
                      f'{os.path.join(testdir.tmpdir, "hello_world_esp32c3")}'
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
        import pytest
        import pexpect
        import re

        def test_expect(dut, pexpect_proc, redirect):
            with redirect():
                print('test1, test2, test3\n')
            dut.expect('test1')
            res = dut.expect('test2')
            assert res.group() == b'test2'
            pexpect_proc.terminate()  # close the pexpect_proc to make a EOF
            res = dut.expect(pexpect.EOF, timeout=None)
            assert res == b', test3'

        def test_expect_exact(dut, pexpect_proc, redirect):
            with redirect():
                 print('test1, test2, test3')
            dut.expect_exact('test1')
            res = dut.expect_exact('test2')
            assert res == b'test2'
            pexpect_proc.terminate()  # close the pexpect_proc to make a EOF
            res = dut.expect_exact(pexpect.EOF, timeout=None)
            assert res == b', test3'

        def test_expect_list(dut, pexpect_proc, redirect):
            with redirect():
                print('test1, test2, test3')
            dut.expect_list([re.compile(b'test4'), re.compile(b'test5'), re.compile(b'test1')])
            res = dut.expect_list([re.compile(b'test4'), re.compile(b'test5'), re.compile(b'test2')])
            assert res.group() == b'test2'
            pexpect_proc.terminate()  # close the pexpect_proc to make a EOF
            res = dut.expect_list([re.compile(b'test4'), re.compile(b'test5'), pexpect.EOF], timeout=None)
            assert res == b', test3'
       """)

    result = testdir.runpytest()

    result.assert_outcomes(passed=3)
