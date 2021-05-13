def test_blink(dut):
    dut.expect('Hash of data verified.')  # expect from what esptool.py printed to sys.stdout
    dut.expect('Turning the LED ON!')
    dut.expect('Turning the LED OFF!')
