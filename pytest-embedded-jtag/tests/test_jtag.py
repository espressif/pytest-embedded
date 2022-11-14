import os

import pytest

jtag_connection_required = pytest.mark.skipif(
    os.getenv('DONT_SKIP_JTAG_TESTS', False) is False,
    reason='Connect the board to a JTAG adapter then ' 'use "DONT_SKIP_JTAG_TESTS" to run this test.',
)


@jtag_connection_required
def test_pexpect_by_jtag(testdir):
    testdir.makepyfile(r"""
        import os
        import time

        def test_pexpect_by_jtag(dut):
            dut.gdb.write('mon reset halt')
            dut.gdb.write('thb app_main')
            dut.gdb.write('c')
            dut.gdb.write('c', non_blocking=True)
            dut.expect('Hello world')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'jtag,idf',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--port', '/dev/ttyUSB1',
        '--part-tool', os.path.join(testdir.tmpdir, 'gen_esp32part.py'),
    )

    result.assert_outcomes(passed=1)
