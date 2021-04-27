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
        'app:',
    ])


def test_fixtures(testdir):
    testdir.makepyfile("""
        import logging

        def test_fixtures_test_file_name(test_file_name):
            assert test_file_name == 'test_fixtures'

        def test_fixtures_test_case_name(test_case_name):
            assert test_case_name == 'test_fixtures_test_case_name'

        def test_fixtures_app(app):
            assert len(app.flash_files) == 3
            assert type(app.partition_table) == dict
            assert type(app.sdkconfig) == dict
    """)
    testdir.chdir()
    result = testdir.runpytest(
        *PLUGINS,
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world'),
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=3)
