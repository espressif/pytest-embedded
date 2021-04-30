PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_jtag',
]


def test_flash(testdir):
    testdir.makepyfile("""
        def test_flash_jtag(capsys, dut):
            dut.flash()
            stdout, _ = capsys.readouterr()
            assert stdout.strip() == 'Flashed by jtag'
    """)

    result = testdir.runpytest(
        *PLUGINS,
    )
    assert result.ret == 0
