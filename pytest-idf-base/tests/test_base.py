def test_help(testdir):
    testdir.monkeypatch.setenv('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')

    result = testdir.runpytest(
        '-p', 'pytest_idf_base',
        '--help'
    )
    result.stdout.fnmatch_lines([
        'idf:',
    ])
