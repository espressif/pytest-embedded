import os

import pytest

jtag_connection_required = pytest.mark.skipif(os.getenv('DONT_SKIP_JTAG_TESTS', False) is False,
                                              reason='Connect the board to a JTAG adapter then '
                                                     'use "DONT_SKIP_JTAG_TESTS" to run this test.')


@jtag_connection_required
def test_pexpect_by_jtag(testdir):
    testdir.makepyfile(r"""
        import os
        import time

        def test_pexpect_by_jtag(dut):
            dut.gdb.gdb_set('mi-async', 'on')
            dut.gdb.file_exec_and_symbols(os.path.join(dut.app.app_path, 'build', 'hello-world.elf'))
            dut.gdb.interpreter_exec_console(f'source {os.path.join(dut.app.app_path, "gdbinit")}')
            dut.expect('hit Temporary breakpoint')

            time.sleep(5)  # wait a while for the breakpoint
            dut.gdb.break_insert('esp_restart')
            dut.expect('\^done,bkpt={number="3",type="breakpoint",disp="keep",enabled="y",addr="0x40081d04",func="esp_restart"')

            dut.gdb.exec_continue_all()
            dut.expect('Restarting now.')
    """)

    result = testdir.runpytest(
        '--embedded-services', 'jtag',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
        '--port', '/dev/ttyUSB1',
    )

    result.assert_outcomes(passed=1)
