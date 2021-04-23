

def test_flash_serial(testdir, test_root):
    testdir.makeconftest("""
        pytest_plugins = [
            'pytest_idf',
            'pytest_idf_flash_serial',
        ]
    """)
    testdir.makepyfile("""
        def test_printf(capsys, dut):
            dut.flash()
            stdout, _ = capsys.readouterr()
            assert stdout.strip() == 'Flashed by serial'
    """)

    result = testdir.runpytest()
    assert result.ret == 0


def test_flash_jtag(testdir, test_root):
    testdir.makeconftest("""
        pytest_plugins = [
            'pytest_idf',
            'pytest_idf_flash_jtag',
        ]
    """)
    testdir.makepyfile("""
        def test_printf(capsys, dut):
            dut.flash()
            stdout, _ = capsys.readouterr()
            assert stdout.strip() == 'Flashed by jtag'
    """)

    result = testdir.runpytest()
    assert result.ret == 0
