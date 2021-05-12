def test_hello_world(dut):
    dut.expect('(100 %)')
    dut.expect('Hello world!')
    dut.expect('Restarting')
