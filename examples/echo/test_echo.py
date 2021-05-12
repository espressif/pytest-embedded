def test_blink(dut):
    dut.write(b'Hello, DUT!')
    dut.expect(b'Hello, DUT!')
