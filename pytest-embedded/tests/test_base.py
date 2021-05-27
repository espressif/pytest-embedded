import os

PLUGINS = [
    '-p', 'pytest_embedded',
]


def test_help(testdir):
    result = testdir.runpytest(
        *PLUGINS,
        '--help'
    )

    result.stdout.fnmatch_lines([
        'embedded:',
    ])


def test_fixtures(testdir):
    testdir.makepyfile("""
        import pytest
        import pexpect

        def test_fixtures_test_file_name(test_file_path):
            assert test_file_path.endswith('test_fixtures.py')

        def test_fixtures_test_case_name(test_case_name):
            assert test_case_name == 'test_fixtures_test_case_name'

        def test_fixtures_app(app):
            assert app.app_path.endswith('hello_world')

        def test_fixtures_dut(dut):
            assert dut.app.app_path.endswith('hello_world')

        def test_fixture_redirect(dut, redirect):
            with redirect:
                print('been redirected')
            dut.expect('been redirected')

            print('not been redirected')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('not been redirected', timeout=1)
    """)

    result = testdir.runpytest(
        *PLUGINS,
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world'),
    )

    result.assert_outcomes(passed=5)
