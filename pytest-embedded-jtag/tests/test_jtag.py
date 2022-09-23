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

        def test_pexpect_by_jtag(dut: IdfDut):
            dut.gdb.write(f'target remote 127.0.0.1:{dut.openocd.gdb_port}')
            dut.gdb.write(f'file {dut.app.elf_file}')
            dut.gdb.write('mon reset halt')
            dut.gdb.write('thb app_main')
            dut.gdb.write('c')
            dut.expect('hit Temporary breakpoint')
            dut.gdb.write('c')
            dut.expect('Hello world!')
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'jtag',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--port', '/dev/ttyUSB1',
    )

    result.assert_outcomes(passed=1)
