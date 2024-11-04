"""Test example for Espressif devices"""

import pytest


@pytest.fixture(autouse=True)
def reset_to_nsh(dut, serial):
    """Resets the device and waits until NSH prompt is ready."""
    serial.hard_reset()
    dut.expect('nsh>', timeout=5)


def test_nuttx_esp_ps(dut):
    dut.write('ps')
    dut.expect('Idle_Task', timeout=2)
