def test_blink(dut):
    dut.expect('(100 %)')
    dut.expect('Turning the LED ON!')
    dut.expect('Turning the LED OFF!')
