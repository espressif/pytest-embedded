import pytest_idf.plugin  # noqa


def test_fixtures(testdir):
    testdir.makepyfile("""
        def test_foo(target, port):
            assert target == ['esp32']
            assert port == '/dev/ttyUSB0'
    """)

    result = testdir.runpytest(
        '--target', 'esp32',
        '--port', '/dev/ttyUSB0',
        '-v',
    )

    result.stdout.fnmatch_lines([
        '*::test_foo PASSED*',
    ])

    assert result.ret == 0


def test_help_message(testdir):
    result = testdir.runpytest(
        '--help',
    )

    result.stdout.fnmatch_lines([
        'idf:',
        '*--target=TARGET*',
        '*--port=PORT*',
    ])
