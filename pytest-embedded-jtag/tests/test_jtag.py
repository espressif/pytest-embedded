import os

import pytest

jtag_connection_required = pytest.mark.skipif(
    os.getenv('DONT_SKIP_JTAG_TESTS', False) is False,
    reason='Connect the board to a JTAG adapter then ' 'use "DONT_SKIP_JTAG_TESTS" to run this test.',
)


@jtag_connection_required
def test_pexpect_multi_source(testdir):
    testdir.makepyfile(r"""
        import os
        import time

        def test_pexpect_multi_source(dut):
            dut.gdb.write('mon reset halt')
            dut.gdb.write('thb app_main')
            dut.gdb.write('thb 23')
            dut.gdb.write('b hello_world_main.c:23')
            dut.gdb.write('b hello_world_main.c:46')
            dut.gdb.write('c')
            dut.gdb.write('c')
            dut.gdb.write('c')
            dut.gdb.write('info local')

            print(dut.expect('i = 10', source='gdb', timeout=10))

            dut.gdb.write('c')
            dut.gdb.write('info local')
            print(dut.expect('i = 9', source='gdb'))

            dut.openocd.write('echo "Hello world from openocd"')

            print(dut.expect('Hello world from openocd', source='openocd'))
            print(dut.expect('Hello world!'))
            print(dut.expect('.*', source='all'))
    """)
    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'esp,idf,jtag',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
    )
    result.assert_outcomes(passed=1)


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
