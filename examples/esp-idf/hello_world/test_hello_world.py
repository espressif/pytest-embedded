def test_hello_world(dut):
    dut.expect('Hash of data verified.')  # expect from what esptool.py printed to sys.stdout
    dut.expect('Hello world!')
    dut.expect('Restarting')
