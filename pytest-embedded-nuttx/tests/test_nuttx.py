import os
import shutil

import pytest


def test_nuttx_app(testdir):
    testdir.makepyfile("""
        import pytest

        def test_nuttx_app(dut, app, target):
            assert 'esp32' == target
            assert '40m' == dut.serial.flash_freq
            assert '4MB' == dut.serial.flash_size
            assert 'dio' == dut.serial.flash_mode

        def test_app_flash(serial, dut):
            serial.erase_flash()
            serial.flash()
            dut.reset_to_nsh()

        def test_hello(dut):
            dut.reset_to_nsh()
            dut.write("ls /dev")
            dut.expect("console")
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'nuttx,esp',
        '--target', 'esp32',
        '--app-path', os.path.join(testdir.tmpdir, "hello_world_nuttx")
    )

    result.assert_outcomes(passed=3)


def test_nuttx_app_mcuboot(testdir):
    testdir.makepyfile("""
        import pytest

        def test_nuttx_app_mcuboot(dut, app, target):
            assert 'esp32' == target
            assert '40m' == dut.serial.flash_freq
            assert '4MB' == dut.serial.flash_size
            assert 'dio' == dut.serial.flash_mode
            assert None != app.bootloader_file

        def test_nuttx_app_mcuboot_flash(serial, dut):
            serial.erase_flash()
            serial.flash()
            dut.reset_to_nsh()

        def test_hello_mcuboot(dut):
            dut.reset_to_nsh()
            dut.write("ls /dev")
            dut.expect("console")
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'nuttx,esp',
        '--target', 'esp32',
        '--app-path', os.path.join(testdir.tmpdir, "hello_world_nuttx_mcuboot")
    )

    result.assert_outcomes(passed=3)


qemu_bin_required = pytest.mark.skipif(
    shutil.which('qemu-system-xtensa') is None,
    reason='Please make sure that `qemu-system-xtensa` is in your PATH env var. Build QEMU for ESP32 locally and then '
           'run `pytest` again'
)

@qemu_bin_required
def test_nuttx_app_qemu(testdir):
    testdir.makepyfile("""
        import pytest
        from time import sleep

        def test_nuttx_app_qemu(dut):
            # Wait boot sequence
            sleep(1)
            dut.write("ls /dev")
            dut.expect("console")
    """)

    efuse_path = os.path.join(testdir.tmpdir, "hello_world_nuttx_qemu", "qemu_efuse.bin")
    qemu_extra = f'-drive file={efuse_path},if=none,format=raw,id=efuse '
    qemu_extra += '-global driver=nvram.esp32.efuse,property=drive,value=efuse'

    print(qemu_extra)
    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'nuttx,qemu',
        '--target', 'esp32',
        '--app-path', os.path.join(testdir.tmpdir, "hello_world_nuttx_qemu"),
        '--qemu-image-path', os.path.join(testdir.tmpdir, "hello_world_nuttx_qemu", "nuttx.merged.bin"),
        '--qemu-extra-args', qemu_extra,
        '--qemu-prog-path', 'qemu-system-xtensa',
    )

    result.assert_outcomes(passed=1)
