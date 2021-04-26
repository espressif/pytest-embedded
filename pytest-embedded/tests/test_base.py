PLUGINS = [
    '-p', 'pytest_embedded',
]


def test_help(testdir):
    result = testdir.runpytest(
        *PLUGINS,
        '--help'
    )

    result.stdout.fnmatch_lines([
        'app:',
    ])


def test_fixtures(testdir):
    testdir.makepyfile("""
        def test_fixtures_test_file_name(test_file_name):
            assert test_file_name == 'test_fixtures'

        def test_fixtures_test_case_name(test_case_name):
            assert test_case_name == 'test_fixtures_test_case_name'
    """)

    result = testdir.runpytest(
        *PLUGINS
    )

    result.assert_outcomes(passed=2)
