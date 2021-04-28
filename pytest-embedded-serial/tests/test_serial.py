import os

PLUGINS = [
    '-p', 'pytest_embedded',
    '-p', 'pytest_embedded_jtag',
    '-p', 'pytest_embedded_serial',
]


def test_flash(testdir):
    testdir.makepyfile("""
        def test_flash_serial(capsys, dut):
            dut.flash()
            stdout, _ = capsys.readouterr()
            assert stdout.strip() == 'Flashed by serial'
    """)

    result = testdir.runpytest(
        *PLUGINS,
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world'),
    )
    assert result.ret == 0
