def test_serial_file_description_leak(testdir):
    testdir.makepyfile(r"""
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


        @pytest.mark.parametrize("fixture", [lazy_fixture("DUT1"), lazy_fixture("DUT2")])
        @pytest.mark.parametrize("test_input", range(0, 300))
        def test_dummy(test_input, dut, fixture):
            dut[0].write("foo")
            assert test_input == test_input

    """)

    result = testdir.runpytest(
        '-s',
        '--count', 2,
        '--embedded-services', 'serial|serial',
        '--port',  '/dev/ttyUSB0|/dev/ttyUSB1',
        '--baud', '115200|115200'
    )
    result.assert_outcomes(passed=600)
