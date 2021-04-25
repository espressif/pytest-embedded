def test_flash_serial(testdir, test_root):
    testdir.monkeypatch.setenv('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')

    testdir.makepyfile("""
        def test_printf(capsys, dut):
            dut.flash()
            stdout, _ = capsys.readouterr()
            assert stdout.strip() == 'Flashed by serial'
    """)

    result = testdir.runpytest(
        '-p', 'pytest_idf_base',
        '-p', 'pytest_idf_flash_serial',
    )
    assert result.ret == 0
