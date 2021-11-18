import logging


def test_hello_world(dut):
    # expect from what esptool.py printed to sys.stdout
    dut.expect('Hash of data verified.')

    # now the `dut.expect` would return a `re.Match` object if succeeded
    res = dut.expect(r'Hello (\w+)!')

    # don't forget to decode, since the serial outputs are all bytes
    logging.info(f'hello to {res.group(1).decode("utf8")}')

    # of course you can just don't care about the return value, do an assert only :)
    dut.expect('Restarting')
