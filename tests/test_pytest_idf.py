import pytest_idf.plugin  # noqa


def test_printf_a(testdir, test_root):
    testdir.makepyfile("""
        def test_printf(capsys, dut):
            assert dut.printf() == 1
    """)

    result = testdir.runpytest('--printf', 'a')

    assert result.ret == 0


def test_printf_b(testdir, test_root):
    testdir.makepyfile("""
        def test_printf(capsys, dut):
            assert dut.printf() == 2
    """)

    result = testdir.runpytest('--printf', 'b')

    assert result.ret == 0
