def test_flash(testdir):
    testdir.monkeypatch.setenv('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')

    testdir.makepyfile("""
        def test_printf(capsys, dut):
            dut.flash()
            stdout, _ = capsys.readouterr()
            assert stdout.strip() == 'Flashed by jtag'
    """)

    result = testdir.runpytest(
        '-p', 'pytest_embedded',
        '-p', 'pytest_embedded_flash_serial',
        '-p', 'pytest_embedded_flash_jtag',
    )
    assert result.ret == 0
