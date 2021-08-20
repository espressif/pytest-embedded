import pytest


@pytest.mark.parametrize(
    'port',
    ['socket://localhost:9876'],
    indirect=True,
)
def test_echo_tcp(dut):
    dut.write(b'Hello, DUT!')
    dut.expect('Hello, DUT!')  # will decode automatically
