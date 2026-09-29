import os
import shutil

import pytest

espemu_bin_required = pytest.mark.skipif(shutil.which('esp-emu') is None, reason='no esp-emu')


@espemu_bin_required
def test_serial_is_the_fixture(testdir):
    testdir.makepyfile("""
        from pytest_embedded_espemu import EspEmuSerial

        def test_serial_is_the_fixture(dut, serial):
            assert isinstance(serial, EspEmuSerial)
            assert dut.serial is serial

            # the serial is built from the port alone, the one the emulator serves
            assert serial.control_port is not None
            assert serial.control_port == dut.espemu.control_port

            # and that is enough to drive it: the reset is answered, not refused
            serial.hard_reset()
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'idf,espemu',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32c3'),
    )

    result.assert_outcomes(passed=1)
