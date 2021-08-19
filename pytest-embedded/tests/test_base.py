import os


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

        def test_fixture_redirect(dut, redirect):
            with redirect('prefix'):
                print('been redirected')
            dut.expect('been redirected')

            print('not been redirected')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('not been redirected', timeout=1)
    """)

    result = testdir.runpytest(
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
    )

    result.assert_outcomes(passed=5)
