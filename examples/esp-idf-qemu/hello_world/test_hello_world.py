import pytest
from pytest_embedded.log import live_print_call


def test_hello_world(dut):
    dut.expect('Hello world!')
    dut.expect('Restarting')


@pytest.mark.parametrize(
    'qemu_extra_args',
    [
        '"-serial tcp::5555,server,nowait -global driver=esp32.gpio,property=strap_mode,value=0x0f"',
    ],
    indirect=True,
)
def test_serial_tcp(dut, redirect):
    with redirect():
        live_print_call('esptool.py --port socket://localhost:5555 --no-stub --chip esp32 read_mac', shell=True)

    dut.expect('Serial port socket://localhost:5555')  # expect from what esptool.py printed to sys.stdout
    dut.expect('MAC:')
    dut.expect('Hard resetting via RTS pin...')
