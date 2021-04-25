def test_help(testdir):
    testdir.monkeypatch.setenv('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')

    result = testdir.runpytest(
        '-p', 'pytest_embedded',
        '--help'
    )
    result.stdout.fnmatch_lines([
        'app:',
    ])
