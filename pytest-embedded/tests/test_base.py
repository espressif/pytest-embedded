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
        def test_fixtures_test_file_name(test_file_name):
            assert test_file_name == 'test_fixtures'

        def test_fixtures_test_case_name(test_case_name):
            assert test_case_name == 'test_fixtures_test_case_name'

        def test_fixtures_app(app):
            assert app.app_path.endswith('hello_world')
    """)
    testdir.chdir()
    result = testdir.runpytest(
        *PLUGINS,
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world'),
    )

    result.assert_outcomes(passed=3)
