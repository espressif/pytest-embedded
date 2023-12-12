import pytest
from pytest_lazyfixture import lazy_fixture

dutHelper = None


class DutHelper:
    def __init__(self):
        self.duts = None

    def setDut(self, duts):
        self.duts = duts

    def dut1(self):
        return self.duts[0]

    def dut2(self):
        return self.duts[1]


@pytest.fixture
def dut_helper(dut):
    global dutHelper
    if dutHelper is None:
        dutHelper = DutHelper()
    dutHelper.setDut(dut)
    return dutHelper


@pytest.fixture
def DUT1(dut_helper):
    return dut_helper.dut1()


@pytest.fixture
def DUT2(dut_helper):
    return dut_helper.dut2()


@pytest.mark.parametrize(

    'embedded_services, count, port, baud', [
        ('serial|serial', 2, '/dev/ttyUSB0|/dev/ttyUSB1', '115200|115200')
    ],
    indirect=True
)
@pytest.mark.parametrize('fixture', [lazy_fixture('DUT1'), lazy_fixture('DUT2')])
@pytest.mark.parametrize('test_input', range(0, 300))
def test_dummy(test_input, dut, fixture):
    dut[0].write('foo')
    assert test_input == test_input
